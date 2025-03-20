"""Fantasy football statistics calculations"""


def f_score(score):
    """Format a score to 2 decimal places

    Args:
        score: The score to format

    Returns:
        Formatted score string with 2 decimal places
    """
    return f"{round(float(score), 2):.2f}"


def get_bench_score(lineup):
    """Calculate total points on a team's bench

    Args:
        lineup: List of players in a team's lineup

    Returns:
        Total bench points as a float
    """
    score = 0
    for player in lineup:
        if player.slot_position == "BE":
            score += player.points
    return round(score, 2)


def get_pos(pos):
    """Normalize position name

    Args:
        pos: Position abbreviation

    Returns:
        Normalized position name
    """
    if pos == "RB/WR/TE":
        return "FLEX"
    return pos


def max_score(lineup):
    """Calculate maximum possible score for a lineup

    Args:
        lineup: List of players in a team's lineup

    Returns:
        Maximum possible score as a float
    """
    positions = {}
    for player in lineup:
        if player.position in positions:
            positions[player.position].append(player.points)
        else:
            positions[player.position] = [player.points]

    # Sort points in each position (highest first)
    for pos in positions:
        positions[pos].sort(reverse=True)

    # Extract top scorers for each position
    try:
        max_qb = positions["QB"].pop(0) if "QB" in positions and positions["QB"] else 0
        max_te = positions["TE"].pop(0) if "TE" in positions and positions["TE"] else 0
        max_dst = (
            positions["D/ST"].pop(0) if "D/ST" in positions and positions["D/ST"] else 0
        )
        max_k = positions["K"].pop(0) if "K" in positions and positions["K"] else 0
        max_p = positions["P"].pop(0) if "P" in positions and positions["P"] else 0

        # Get top 2 RBs and WRs
        max_rb = sum(
            [
                positions["RB"].pop(0) if "RB" in positions and positions["RB"] else 0,
                positions["RB"].pop(0) if "RB" in positions and positions["RB"] else 0,
            ]
        )
        max_wr = sum(
            [
                positions["WR"].pop(0) if "WR" in positions and positions["WR"] else 0,
                positions["WR"].pop(0) if "WR" in positions and positions["WR"] else 0,
            ]
        )

        # Get flex (best of remaining RB/WR/TE)
        max_flex = 0
        if (
            "WR" in positions
            and positions["WR"]
            and "RB" in positions
            and positions["RB"]
        ):
            max_flex = max(positions["WR"].pop(0), positions["RB"].pop(0))
        elif "WR" in positions and positions["WR"]:
            max_flex = positions["WR"].pop(0)
        elif "RB" in positions and positions["RB"]:
            max_flex = positions["RB"].pop(0)

        return round(
            max_qb + max_te + max_dst + max_k + max_p + max_rb + max_wr + max_flex, 2
        )
    except Exception as e:
        print(f"Error calculating max score: {e}")
        return 0


def points_per_player_per_position(lineup):
    """Calculate points per player per position

    Args:
        lineup: List of players in a team's lineup

    Returns:
        Dictionary containing position stats
    """
    pppp = {}
    for player in lineup:
        pos = get_pos(player.slot_position)
        if player.slot_position == "BE":
            pos = pos + "-" + player.position

        if pos in pppp:
            pppp[pos]["points"] += player.points
            pppp[pos]["point_arr"].append(player.points)
            pppp[pos]["proj_points"] += player.projected_points
            pppp[pos]["count"] += 1
            pppp[pos]["min"] = min(pppp[pos]["min"], player.points)
            pppp[pos]["max"] = max(pppp[pos]["max"], player.points)
            pppp[pos]["avg"] = pppp[pos]["points"] / pppp[pos]["count"]

            pppp[pos]["proj_min"] = min(pppp[pos]["proj_min"], player.projected_points)
            pppp[pos]["proj_max"] = max(pppp[pos]["proj_max"], player.projected_points)
            pppp[pos]["proj_avg"] = pppp[pos]["proj_points"] / pppp[pos]["count"]
        else:
            pppp[pos] = {
                "points": player.points,
                "point_arr": [player.points],
                "proj_points": player.projected_points,
                "position": pos,
                "count": 1,
                "min": player.points,
                "max": player.points,
                "avg": player.points,
                "proj_min": player.projected_points,
                "proj_max": player.projected_points,
                "proj_avg": player.projected_points,
            }

    return pppp


def calculate_weekly_scores(box_score):
    """Calculate all team scores for the week

    Args:
        box_score: List of box score objects

    Returns:
        List of team score dictionaries
    """
    scores = []
    for score in box_score:
        scores.append(
            {
                "score": score.home_score,
                "name": score.home_team.team_name,
                "abbrev": score.home_team.team_abbrev,
                "won": score.home_score > score.away_score,
                "division": score.home_team.division_name[:1],
                "bench_score": get_bench_score(score.home_lineup),
                "max_score": max_score(score.home_lineup),
                "lineup": score.home_lineup,
                "logo": score.home_team.logo_url,
            }
        )
        scores.append(
            {
                "score": score.away_score,
                "name": score.away_team.team_name,
                "abbrev": score.away_team.team_abbrev,
                "won": score.away_score > score.home_score,
                "division": score.away_team.division_name[:1],
                "bench_score": get_bench_score(score.away_lineup),
                "max_score": max_score(score.away_lineup),
                "lineup": score.away_lineup,
                "logo": score.away_team.logo_url,
            }
        )

    return scores


def calculate_matchups(box_score):
    """Calculate matchup data for the week

    Args:
        box_score: List of box score objects

    Returns:
        List of matchup dictionaries
    """
    matchups = []
    for score in box_score:
        home_max = max_score(score.home_lineup)
        away_max = max_score(score.away_lineup)

        home_bench = get_bench_score(score.home_lineup)
        away_bench = get_bench_score(score.away_lineup)

        home_bench_outscored = home_bench > score.home_score
        away_bench_outscored = away_bench > score.away_score

        # Determine if losing team could have won with optimal lineup
        lost_could_win = False
        if score.home_score > score.away_score and away_max > score.home_score:
            lost_could_win = True
        elif score.away_score > score.home_score and home_max > score.away_score:
            lost_could_win = True

        matchups.append(
            {
                "home_team": {
                    "name": score.home_team.team_name,
                    "abbrev": score.home_team.team_abbrev,
                    "score": score.home_score,
                    "bench": home_bench,
                    "max_score": home_max,
                    "bench_outscored": home_bench_outscored,
                    "lineup": score.home_lineup,
                    "logo": score.home_team.logo_url,
                    "division": score.home_team.division_name[:1],
                },
                "away_team": {
                    "name": score.away_team.team_name,
                    "abbrev": score.away_team.team_abbrev,
                    "score": score.away_score,
                    "bench": away_bench,
                    "max_score": away_max,
                    "bench_outscored": away_bench_outscored,
                    "lineup": score.away_lineup,
                    "logo": score.away_team.logo_url,
                    "division": score.away_team.division_name[:1],
                },
                "winner": (
                    "home"
                    if score.home_score > score.away_score
                    else "away" if score.away_score > score.home_score else "tie"
                ),
                "lost_could_win": lost_could_win,
            }
        )

    return matchups
