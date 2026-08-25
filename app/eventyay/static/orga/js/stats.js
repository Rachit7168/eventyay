const globalData = document.getElementById("global-data")
const dataMapping = globalData && globalData.dataset.mapping ? JSON.parse(globalData.dataset.mapping) : {}
let searchUrl = globalData && globalData.dataset.url ? globalData.dataset.url : ""

/* ─── Timeline (area chart) ─────────────────────────────────────────────── */
const drawTimeline = (targetId, elementIds) => {
    const targetElement = document.getElementById(targetId)
    if (!targetElement) return null

    const dataElements = elementIds
        .map((id) => document.getElementById(id))
        .filter((element) => element && element.dataset.timeline)

    if (!dataElements.length) return null

    const annotations = globalData && globalData.dataset.annotations ? globalData.dataset.annotations : '{"deadlines":[]}'
    const deadlines = JSON.parse(annotations).deadlines.map(
        (element) => {
            return {
                x: new Date(element[0]).getTime(),
                borderColor: "#ff4560",
                strokeDashArray: 0,
                label: {
                    style: {
                        borderColor: "#ff4560",
                        background: "#ff4560",
                        color: "#fff",
                        fontSize: "14px",
                        padding: { top: 5 },
                    },
                    text: element[1],
                },
            }
        },
    )
    let options = {
        series: dataElements.map((element) => {
            let parsedData = JSON.parse(element.dataset.timeline).map((element) => {
                return { x: new Date(element.x).getTime(), y: element.y }
            })
            
            parsedData.sort((a, b) => a.x - b.x)
            
            if (parsedData.length > 0) {
                const ONE_DAY = 86400000
                const firstTime = parsedData[0].x
                parsedData.unshift({ x: firstTime - ONE_DAY, y: 0 })
                
                const lastTime = parsedData[parsedData.length - 1].x
                parsedData.push({ x: lastTime + ONE_DAY, y: 0 })
            }
            
            return {
                name: element.dataset.label,
                data: parsedData,
            }
        }),
        xaxis: {
            type: "datetime",
            tooltip: { enabled: false },
            labels: {
                datetimeUTC: false,
                format: "dd MMM",
                datetimeFormatter: {
                    year: "yyyy",
                    month: "MMM yyyy",
                    day: "dd MMM",
                    hour: "HH:mm",
                },
                style: { fontWeight: 400, fontSize: "11px", colors: "#9ca3af" },
            },
            axisBorder: { show: false },
            axisTicks: { show: false },
        },
        yaxis: {
            labels: {
                style: { fontSize: "11px", colors: "#9ca3af" },
            },
        },
        annotations: { xaxis: deadlines },
        chart: {
            redrawOnParentResize: true,
            height: 220,
            type: "area",
            toolbar: { show: false },
            sparkline: { enabled: false },
        },
        colors: ["#2185d0", "#22c55e", "#ef4444"],
        fill: { type: ["gradient", "gradient", "gradient"] },
        stroke: { width: 2, curve: "smooth" },
        dataLabels: { enabled: false },
        legend: {
            formatter: function (val, opts) {
                if (val.length > 15) val = val.slice(0, 15) + "…"
                return val
            },
            position: "top",
            horizontalAlign: "left",
            fontSize: "12px",
            markers: { width: 8, height: 8, radius: 4 },
        },
        grid: {
            borderColor: "#f3f4f6",
            strokeDashArray: 3,
            padding: { left: 4, right: 4 },
        },
        tooltip: {
            enabled: true,
            shared: true,
            x: { show: true, format: "dd MMM yyyy" },
            marker: { show: true },
        },
    }
    const chart = new ApexCharts(targetElement, options)
    chart.render()

    // ── Inject Summary Stats ──
    const isTalk = targetId.includes("talk")
    let totalCount = 0
    let peakCount = 0
    let peakDate = "-"
    
    const timelineData = options.series[0]?.data || []
    timelineData.forEach(d => {
        totalCount += d.y
        if (d.y > peakCount) {
            peakCount = d.y
            const dateObj = new Date(d.x)
            peakDate = dateObj.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
        }
    })

    let acceptedRate = "0.0%"
    const stateDataPrefix = isTalk ? "talk" : "submission"
    const stateDataEl = document.getElementById(stateDataPrefix + "-state-data")
    if (stateDataEl && stateDataEl.dataset.states) {
        const states = JSON.parse(stateDataEl.dataset.states)
        let accepted = 0
        let total = 0
        states.forEach(s => {
            total += s.value
            if (s.label.toLowerCase() === 'accepted' || s.label.toLowerCase() === 'confirmed') {
                accepted += s.value
            }
        })
        if (total > 0) acceptedRate = ((accepted / total) * 100).toFixed(1) + "%"
    }

    if (totalCount >= 0) {
        const labelName = isTalk ? "Total sessions" : "Total submitted"
        const peakText = peakCount > 0 ? `${peakDate}, ${peakCount}` : "-"
        const summaryHtml = `
            <div class="td-timeline-summary">
                <div class="td-ts-item">
                    <div class="td-ts-label">${labelName}</div>
                    <div class="td-ts-value">${totalCount}</div>
                </div>
                <div class="td-ts-item">
                    <div class="td-ts-label">Peak day</div>
                    <div class="td-ts-value">${peakText}</div>
                </div>
                <div class="td-ts-item">
                    <div class="td-ts-label">Accepted rate</div>
                    <div class="td-ts-value">${acceptedRate}</div>
                </div>
            </div>
        `
        targetElement.parentElement.insertAdjacentHTML('beforeend', summaryHtml)
    }

    return chart
}

/* ─── Data helpers ──────────────────────────────────────────────────────── */
const getPieData = (id) => {
    const element = document.getElementById(id)
    if (!element || !element.dataset.states) return null
    const data = JSON.parse(element.dataset.states)
    if (!data || !data.length) return null
    return {
        series: data.map((e) => e.value),
        labels: data.map((e) => e.label),
    }
}

/* ─── Horizontal Bar Chart ──────────────────────────────────────────────── */
const drawHBarChart = (data, elementId, clickType) => {
    const element = document.getElementById(elementId)
    if (!element || !data || !data.series || !data.series.length) return null

    // Sort descending by value
    const combined = data.labels.map((label, i) => ({ label, value: data.series[i] }))
    combined.sort((a, b) => b.value - a.value)

    const chartHeight = Math.max(combined.length * 34 + 50, 160)

    const options = {
        series: [{ name: "Count", data: combined.map((d) => d.value) }],
        chart: {
            type: "bar",
            height: chartHeight,
            width: "100%",
            redrawOnParentResize: true,
            toolbar: { show: false },
            events: {
                dataPointSelection: (event, chartContext, config) => {
                    if (!clickType || !dataMapping[clickType]) return
                    const typeMapping = { track: "track", type: "submission_type", state: "state", language: "content_locale" }
                    const label = combined[config.dataPointIndex].label
                    const searchValue = dataMapping[clickType][label]
                    if (searchValue) {
                        window.location.href = searchUrl + "&" + typeMapping[clickType] + "=" + searchValue
                    }
                },
                dataPointMouseEnter: () => { element.style.cursor = "pointer" },
                dataPointMouseLeave: () => { element.style.cursor = "inherit" },
            },
        },
        plotOptions: {
            bar: {
                horizontal: true,
                barHeight: "55%",
                borderRadius: 3,
                dataLabels: { position: "top" },
            },
        },
        dataLabels: {
            enabled: true,
            offsetX: 25,
            textAnchor: 'start',
            style: { fontSize: "12px", fontWeight: 600, colors: ["#374151"] },
            background: { enabled: false },
        },
        xaxis: {
            categories: combined.map((d) => d.label),
            labels: { style: { fontSize: "11px", colors: "#9ca3af" } },
            axisBorder: { show: false },
            axisTicks: { show: false },
        },
        yaxis: {
            labels: {
                style: { fontSize: "11.5px", colors: "#374151", fontWeight: 500 },
                maxWidth: 130,
            },
        },
        colors: ["#2185d0"],
        grid: {
            borderColor: "#f3f4f6",
            xaxis: { lines: { show: true } },
            yaxis: { lines: { show: false } },
            padding: { left: 0, right: 40 },
        },
        tooltip: {
            enabled: true,
            x: { show: false },
            y: { formatter: (val) => val + " sessions" },
        },
        legend: { show: false },
    }

    const chart = new ApexCharts(element, options)
    chart.render()

    // Add summary to fill the space
    const totalCount = combined.reduce((a, b) => a + b.value, 0)
    const uniqueCount = combined.length
    const topItem = combined[0] ? combined[0].label : '-'
    
    let typeLabel = 'Items'
    let typeLabelSingular = 'Item'
    if (clickType === 'type') { typeLabel = 'Types'; typeLabelSingular = 'Type'; }
    else if (clickType === 'track') { typeLabel = 'Tracks'; typeLabelSingular = 'Track'; }

    let shortTopItem = topItem
    if (shortTopItem.length > 20) shortTopItem = shortTopItem.substring(0, 17) + "..."

    const summaryHtml = `
        <div class="td-timeline-summary">
            <div class="td-ts-item" title="${topItem}">
                <div class="td-ts-label">Top ${typeLabelSingular}</div>
                <div class="td-ts-value" style="font-size: 13px; line-height: 22px;">${shortTopItem}</div>
            </div>
            <div class="td-ts-item">
                <div class="td-ts-label">Total ${typeLabel}</div>
                <div class="td-ts-value">${uniqueCount}</div>
            </div>
            <div class="td-ts-item">
                <div class="td-ts-label">Total sessions</div>
                <div class="td-ts-value">${totalCount}</div>
            </div>
        </div>
    `
    // Wait a tick for the DOM, then append if wrapper exists
    setTimeout(() => {
        const wrap = element.closest('.td-analytics-card')
        if (wrap) {
            wrap.insertAdjacentHTML('beforeend', summaryHtml)
        }
    }, 100)

    return chart
}

/* ─── Stats Table (language / state) ───────────────────────────────────── */
const PALETTE = ["#2185d0", "#f97316", "#22c55e", "#8b5cf6", "#ef4444", "#06b6d4", "#f59e0b", "#ec4899", "#10b981", "#a78bfa"]

const drawStatsTable = (data, elementId) => {
    const element = document.getElementById(elementId)
    if (!element || !data || !data.series || !data.series.length) return

    const total = data.series.reduce((a, b) => a + b, 0)

    // Sort descending
    const rows = data.labels.map((label, i) => ({ label, value: data.series[i] }))
    rows.sort((a, b) => b.value - a.value)

    let html = `<table class="td-stats-table">
        <thead><tr>
            <th colspan="2">Name</th>
            <th class="td-st-count">Count</th>
            <th class="td-st-pct">%</th>
        </tr></thead>
        <tbody>`

    rows.forEach(({ label, value }, i) => {
        const pct = total > 0 ? ((value / total) * 100).toFixed(1) : "0.0"
        const color = PALETTE[i % PALETTE.length]
        html += `<tr>
            <td class="td-st-dot"><span style="background:${color}"></span></td>
            <td class="td-st-name">${label}</td>
            <td class="td-st-count">${value}</td>
            <td class="td-st-pct">${pct}%</td>
        </tr>`
    })

    html += `</tbody>
        <tfoot><tr>
            <td colspan="2"><strong>Total</strong></td>
            <td class="td-st-count"><strong>${total}</strong></td>
            <td class="td-st-pct"><strong>100%</strong></td>
        </tr></tfoot>
    </table>`

    // View-all link if exists
    const linkEl = element.closest(".td-analytics-card")?.querySelector(".td-analytics-view-all")
    if (linkEl) linkEl.style.display = "block"

    element.innerHTML = html
}

/* ─── Legacy donut (kept for any page that still uses it) ───────────────── */
const drawPieChart = (data, scope, type) => {
    const id = scope + "-" + type
    const element = document.getElementById(id)
    if (!element || !element.classList.contains("pie")) return null
    if (!data || !data.series || !data.series.length) return null

    const typeMapping = { track: "track", type: "submission_type", state: "state", language: "content_locale" }
    const options = {
        series: data.series,
        labels: data.labels,
        chart: {
            height: 300,
            width: "100%",
            redrawOnParentResize: true,
            type: "donut",
            events: {
                dataPointSelection: (event, chartContext, config) => {
                    if (!dataMapping[type]) return
                    const label = config.w.config.labels[config.dataPointIndex]
                    const searchValue = dataMapping[type][label]
                    if (searchValue) window.location.href = searchUrl + "&" + typeMapping[type] + "=" + searchValue
                },
                dataPointMouseEnter: () => { element.style.cursor = "pointer" },
                dataPointMouseLeave: () => { element.style.cursor = "inherit" },
            },
        },
        dataLabels: { enabled: false },
        legend: {
            position: "bottom",
            formatter: (val, opts) => {
                if (val.length > 20) val = val.slice(0, 20) + "…"
                return val + " – " + opts.w.globals.series[opts.seriesIndex]
            },
        },
        plotOptions: {
            pie: {
                customScale: 0.85,
                donut: { labels: { show: true, name: { formatter: (val) => val.length > 15 ? val.slice(0, 15) + "…" : val } } },
            },
        },
        tooltip: { enabled: false },
    }
    const chart = new ApexCharts(element, options)
    chart.render()
    return chart
}

/* ─── Main render ───────────────────────────────────────────────────────── */
let chartTypes = ["state"]
if (dataMapping.type) chartTypes.push("type")
if (dataMapping.track) chartTypes.push("track")
if (dataMapping.language) chartTypes.push("language")

const renderAllCharts = () => {
    // ── Timelines ──
    if (document.getElementById("proposal-timeline")) {
        drawTimeline("proposal-timeline", ["submission-timeline-data"])
    } else if (document.getElementById("timeline")) {
        drawTimeline("timeline", ["submission-timeline-data"])
    }
    if (document.getElementById("talk-timeline")) {
        drawTimeline("talk-timeline", ["talk-timeline-data"])
    }

    // ── Horizontal bar charts: type & track ──
    const barTypes = ["type", "track"]
    barTypes.forEach((t) => {
        const subData = getPieData("submission-" + t + "-data")
        if (subData) drawHBarChart(subData, "submission-" + t + "-chart", t)

        const talkData = getPieData("talk-" + t + "-data")
        if (talkData) drawHBarChart(talkData, "talk-" + t + "-chart", t)
    })

    // ── Tables: language & state ──
    const tableTypes = ["language", "state"]
    tableTypes.forEach((t) => {
        const subData = getPieData("submission-" + t + "-data")
        if (subData) drawStatsTable(subData, "submission-" + t + "-table")

        const talkData = getPieData("talk-" + t + "-data")
        if (talkData) drawStatsTable(talkData, "talk-" + t + "-table")
    })

    // ── Legacy pie (any .pie element still present) ──
    chartTypes.forEach((item) => {
        const subData = getPieData("submission-" + item + "-data")
        if (subData) drawPieChart(subData, "submission", item)
        const talkData = getPieData("talk-" + item + "-data")
        if (talkData) drawPieChart(talkData, "talk", item)
    })
}

setTimeout(renderAllCharts, 10)
