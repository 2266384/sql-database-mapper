
document.addEventListener("DOMContentLoaded", function () {

    const viewport = document.getElementById("diagram-viewport");
    const content = document.getElementById("diagram-content");
    const zoomLevel = document.getElementById("zoom-level");

    if (!viewport || !content) return;

    let scale = 1;
    let isDragging = false;
    let startX = 0;
    let startY = 0;
    let scrollLeft = 0;
    let scrollTop = 0;

    const MIN_ZOOM = 0.2;
    const MAX_ZOOM = 3;
    const ZOOM_STEP = 0.1;

    function updateZoom() {
        content.style.transform = `scale(${scale})`;
        zoomLevel.textContent = `${Math.round(scale * 100)}%`;
    }

    function setZoom(newScale) {
        scale = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, newScale));
        updateZoom();
    }

    document.getElementById("zoom-in").addEventListener("click", () => {
        setZoom(scale + ZOOM_STEP);
    });

    document.getElementById("zoom-out").addEventListener("click", () => {
        setZoom(scale - ZOOM_STEP);
    });

    document.getElementById("zoom-reset").addEventListener("click", () => {
        setZoom(1);
        viewport.scrollTo(0, 0);
    });

    document.getElementById("zoom-fit").addEventListener("click", () => {

        const svg = content.querySelector("svg");

        if (!svg) return;

        const svgWidth = svg.getBBox().width;
        const svgHeight = svg.getBBox().height;

        if (!svgWidth || !svgHeight) return;

        const availableWidth = viewport.clientWidth - 30;
        const availableHeight = viewport.clientHeight - 30;

        const fitScale = Math.min(
            availableWidth / svgWidth,
            availableHeight / svgHeight,
            1
        );

        setZoom(fitScale);
        viewport.scrollTo(0, 0);
    });

    // Mouse-wheel zoom
    viewport.addEventListener("wheel", function (event) {

        if (!event.ctrlKey && !event.metaKey) return;

        event.preventDefault();

        const rect = viewport.getBoundingClientRect();

        const mouseX = event.clientX - rect.left + viewport.scrollLeft;
        const mouseY = event.clientY - rect.top + viewport.scrollTop;

        const oldScale = scale;
        const newScale = Math.min(
            MAX_ZOOM,
            Math.max(MIN_ZOOM, scale + (event.deltaY < 0 ? ZOOM_STEP : -ZOOM_STEP))
        );

        setZoom(newScale);

        viewport.scrollLeft =
            mouseX * (newScale / oldScale) - (event.clientX - rect.left);

        viewport.scrollTop =
            mouseY * (newScale / oldScale) - (event.clientY - rect.top);

    }, { passive: false });

    // Click and drag to pan
    viewport.addEventListener("mousedown", function (event) {

        if (event.button !== 0) return;

        isDragging = true;
        startX = event.pageX;
        startY = event.pageY;
        scrollLeft = viewport.scrollLeft;
        scrollTop = viewport.scrollTop;

    });

    document.addEventListener("mouseup", () => {
        isDragging = false;
    });

    document.addEventListener("mousemove", function (event) {

        if (!isDragging) return;

        event.preventDefault();

        viewport.scrollLeft = scrollLeft - (event.pageX - startX);
        viewport.scrollTop = scrollTop - (event.pageY - startY);

    });

    updateZoom();

});
