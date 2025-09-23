import os
import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# League configuration
CUR_YEAR = datetime.datetime.now().date().strftime("%Y")
LEAGUE_ID = int(os.environ.get("LEAGUE_ID"))
LEAGUE_YEAR = int(os.environ.get("LEAGUE_YEAR", CUR_YEAR))
SWID = os.environ.get("swid")
ESPN_S2 = os.environ.get("espn_s2")

# Report configuration
DEFAULT_WEEK = int(os.environ.get("DEFAULT_WEEK", 0))

# Division images for HTML reports
DIV_IMAGES = {"J": '<img src="./jag-16x16.png">', "F": '<img src="./fball-16x16.png">'}
