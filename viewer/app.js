document.addEventListener('DOMContentLoaded', () => {
    const yearSelect = document.getElementById('year-select');
    const weekSelect = document.getElementById('week-select');
    const reportFrame = document.getElementById('report-frame');

    let reportsData = {};

    yearSelect.addEventListener('change', () => {
        const newYear = yearSelect.value;
        const currentWeek = weekSelect.value;

        populateWeekSelector(newYear);

        const newYearWeeks = reportsData[newYear].map(String);
        if (newYearWeeks.includes(currentWeek)) {
            weekSelect.value = currentWeek;
        } else {
            weekSelect.value = newYearWeeks[0];
        }
        loadReport(newYear, weekSelect.value);
    });

    weekSelect.addEventListener('change', () => {
        loadReport(yearSelect.value, weekSelect.value);
    });

    window.addEventListener('hashchange', handleHashChange);

    fetch('reports.json')
        .then(response => response.json())
        .then(data => {
            reportsData = data;
            populateYearSelector();
            handleHashChange(); // Load initial report based on hash or latest
        })
        .catch(error => {
            console.error('Error loading reports.json:', error);
            reportFrame.src = 'about:blank';
            reportFrame.contentDocument.write("Could not load reports. Please run the build script.");
        });

    function populateYearSelector() {
        const years = Object.keys(reportsData).sort((a, b) => b - a);
        years.forEach(year => {
            const option = document.createElement('option');
            option.value = year;
            option.textContent = year;
            yearSelect.appendChild(option);
        });
    }

    function populateWeekSelector(year) {
        if (!reportsData[year]) return;
        weekSelect.innerHTML = '';
        const weeks = reportsData[year].sort((a, b) => a - b);
        weeks.forEach(week => {
            const option = document.createElement('option');
            option.value = week;
            option.textContent = `Week ${week}`;
            weekSelect.appendChild(option);
        });
    }

    function loadReport(year, week, updateHash = true) {
        if (!year || !week) return;
        const reportPath = `reports/${year}-week${week}.html`;
        reportFrame.src = reportPath;
        if (updateHash) {
            window.location.hash = `${year}-${week}`;
        }
    }

    function loadLatestReport() {
        const latestYear = Object.keys(reportsData).sort((a, b) => b - a)[0];
        if (!latestYear) return;

        const latestWeek = reportsData[latestYear].sort((a, b) => b - a)[0];

        yearSelect.value = latestYear;
        populateWeekSelector(latestYear);
        weekSelect.value = latestWeek;
        loadReport(latestYear, latestWeek);
    }

    function handleHashChange() {
        const hash = window.location.hash.substring(1);
        if (!hash) {
            loadLatestReport();
            return;
        }

        const [year, week] = hash.split('-');

        if (year && week && reportsData[year] && reportsData[year].map(String).includes(week)) {
            yearSelect.value = year;
            populateWeekSelector(year);
            weekSelect.value = week;
            loadReport(year, week, false); // Don't update hash again
        } else {
            loadLatestReport();
        }
    }
});
