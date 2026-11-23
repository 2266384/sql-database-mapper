
mermaid.initialize({

    startOnLoad: false,

    theme: 'base',

    themeVariables: {
        background: '#F4F8FA',
        fontFamily: 'Nunito, sans-serif',
        fontSize: '13px',

        primaryColor: '#FFFFFF',
        primaryTextColor: '#263746',
        primaryBorderColor: '#0072BC',

        lineColor: '#399BC1',
        textColor: '#263746'
    },

    er: {
        theme: 'default',
        look: 'classic',
        diagramPadding: 30,
        layoutDirection: 'TB',
        minEntityWidth: 140,
        minEntityHeight: 75
    },

    securityLevel: 'strict'

});


/* =========================================
   Apply custom SVG styling
========================================= */

function styleMermaidDiagram() {

    const svg = document.querySelector('#diagram-content svg');

    if (!svg) return;

    svg.querySelectorAll('.node.default').forEach(node => {

        const outerPath = node.querySelector('.outer-path');
        const firstRow = node.querySelector(
            '.row-rect-odd, .row-rect-even'
        );

        if (!outerPath || !firstRow) return;

        const paths = outerPath.querySelectorAll('path');

        if (paths.length < 2) return;

        const backgroundPath = paths[0];
        const borderPath = paths[1];

        // Style the entity background.
        backgroundPath.style.fill = '#FFFFFF';
        backgroundPath.style.stroke = 'none';

        // Style the entity outline.
        borderPath.style.fill = 'none';
        borderPath.style.stroke = '#0072BC';
        borderPath.style.strokeWidth = '1.8px';
        borderPath.style.strokeLinejoin = 'round';

        /*
         * Create the header background.
         * Remove an existing header first so this
         * function can safely be called more than once.
         */

        node.querySelectorAll('.custom-entity-header').forEach(
            element => element.remove()
        );

        try {

            const outerBounds = backgroundPath.getBBox();

            const firstRowPath = firstRow.querySelector('path');

            if (!firstRowPath) return;

            const rowBounds = firstRowPath.getBBox();

            const x = outerBounds.x;
            const y = outerBounds.y;
            const width = outerBounds.width;
            const height = rowBounds.y - outerBounds.y;

            if (width <= 0 || height <= 0) return;

            // Rounded top corners only.
            const radius = 5;

            const header = document.createElementNS(
                'http://www.w3.org/2000/svg',
                'path'
            );

            header.setAttribute('class', 'custom-entity-header');

            header.setAttribute(
                'd',
                [
                    `M ${x + radius} ${y}`,
                    `H ${x + width - radius}`,
                    `Q ${x + width} ${y} ${x + width} ${y + radius}`,
                    `V ${y + height}`,
                    `H ${x}`,
                    `V ${y + radius}`,
                    `Q ${x} ${y} ${x + radius} ${y}`,
                    'Z'
                ].join(' ')
            );

            header.setAttribute('fill', '#0072BC');
            header.setAttribute('stroke', 'none');
            header.setAttribute('pointer-events', 'none');

            // Place the header behind the entity labels and rows.
            node.insertBefore(
                header,
                firstRow
            );

        } catch (error) {

            console.warn(
                'Unable to style Mermaid entity header:',
                error
            );

        }

    });


    svg.querySelectorAll('.node.default').forEach(node => {
        const outerPath = node.querySelector('.outer-path path:nth-child(2)');
        if (!outerPath) return;
        
        const bbox = outerPath.getBBox();
        const radius = 6;
        
        const x = bbox.x;
        const y = bbox.y;
        const width = bbox.width;
        const height = bbox.height;
        
        outerPath.setAttribute(
            'd',
            `
            M ${x + radius} ${y}
            H ${x + width - radius}
            Q ${x + width} ${y} ${x + width} ${y + radius}
            V ${y + height - radius}
            Q ${x + width} ${y + height} ${x + width - radius} ${y + height}
            H ${x + radius}
            Q ${x} ${y + height} ${x} ${y + height - radius}
            V ${y + radius}
            Q ${x} ${y} ${x + radius} ${y}
            Z
            `
        );
    });


    /* =========================================
       Style PK / FK / UK Labels
    ========================================= */
    
    svg.querySelectorAll('.label.attribute-keys').forEach(label => {
    
        const foreignObject = label.querySelector('foreignObject');
    
        if (!foreignObject) return;
    
        const textElement = foreignObject.querySelector('p');
    
        if (!textElement) return;
    
        const keys = textElement.textContent
            .split(',')
            .map(key => key.trim())
            .filter(Boolean);
    
        if (!keys.length) return;
    
        // Create badge container
        const container = document.createElement('span');
    
        container.className = 'key-badge-container';
    
        keys.forEach(key => {
        
            const badge = document.createElement('span');
        
            badge.className = `key-badge ${key.toLowerCase()}`;
            badge.textContent = key;
        
            container.appendChild(badge);
        
        });
    
        // Replace original Mermaid label
        textElement.replaceChildren(container);
    
        /*
         * Reserve space for horizontal badges.
         *
         * Available space before the comment column:
         * Approximately 66.9px.
         */
        foreignObject.setAttribute('width', '58');
    
    });

}

/* =========================================
   Diagram Zoom and Pan State
========================================= */

let diagramScale = 1;
let diagramFitScale = 1;

const MIN_ZOOM = 0.1;
const MAX_ZOOM = 4;
const ZOOM_FACTOR = 1.2;
const DIAGRAM_PADDING = 35;


/* =========================================
   Apply Diagram Scale
========================================= */

function applyDiagramScale(scale) {

    const viewport = document.getElementById('diagram-viewport');
    const stage = document.getElementById('diagram-stage');
    const content = document.getElementById('diagram-content');

    if (!viewport || !stage || !content) return;

    diagramScale = Math.min(
        Math.max(scale, MIN_ZOOM),
        MAX_ZOOM
    );

    const naturalWidth = content.offsetWidth;
    const naturalHeight = content.offsetHeight;

    content.style.transform = `scale(${diagramScale})`;

    stage.style.width = `${naturalWidth * diagramScale}px`;
    stage.style.height = `${naturalHeight * diagramScale}px`;
}


/* =========================================
   Zoom Diagram
========================================= */

function zoomDiagram(factor, anchorX, anchorY) {

    const viewport = document.getElementById('diagram-viewport');

    if (!viewport) return;

    const previousScale = diagramScale;

    const newScale = Math.min(
        Math.max(previousScale * factor, MIN_ZOOM),
        MAX_ZOOM
    );

    if (newScale === previousScale) return;

    // Maintain the point beneath the cursor
    const scaleRatio = newScale / previousScale;

    const scrollLeft = (viewport.scrollLeft + anchorX) * scaleRatio - anchorX;
    const scrollTop = (viewport.scrollTop + anchorY) * scaleRatio - anchorY;

    applyDiagramScale(newScale);

    viewport.scrollLeft = scrollLeft;
    viewport.scrollTop = scrollTop;
}


/* =========================================
   Diagram Mouse Controls
========================================= */

function setupDiagramControls() {

    const viewport = document.getElementById('diagram-viewport');

    if (!viewport) return;

    // Mouse-wheel zoom
    viewport.addEventListener('wheel', (event) => {

        event.preventDefault();

        const rect = viewport.getBoundingClientRect();

        const anchorX = event.clientX - rect.left;
        const anchorY = event.clientY - rect.top;

        const factor = event.deltaY < 0
            ? ZOOM_FACTOR
            : 1 / ZOOM_FACTOR;

        zoomDiagram(factor, anchorX, anchorY);

    }, { passive: false });


    // Drag to pan
    let isDragging = false;
    let startX = 0;
    let startY = 0;
    let startScrollLeft = 0;
    let startScrollTop = 0;

    viewport.addEventListener('mousedown', (event) => {

        if (event.button !== 0) return;

        isDragging = true;

        startX = event.clientX;
        startY = event.clientY;

        startScrollLeft = viewport.scrollLeft;
        startScrollTop = viewport.scrollTop;

        viewport.style.cursor = 'grabbing';

        event.preventDefault();

    });

    window.addEventListener('mousemove', (event) => {

        if (!isDragging) return;

        viewport.scrollLeft = startScrollLeft - (event.clientX - startX);
        viewport.scrollTop = startScrollTop - (event.clientY - startY);

    });

    window.addEventListener('mouseup', () => {

        isDragging = false;
        viewport.style.cursor = 'grab';

    });

    viewport.style.cursor = 'grab';
}


/* =========================================
   Diagram Zoom Buttons
========================================= */

function setupZoomButtons() {

    document.getElementById('zoom-in')?.addEventListener('click', () => {

        const viewport = document.getElementById('diagram-viewport');

        zoomDiagram(
            ZOOM_FACTOR,
            viewport.clientWidth / 2,
            viewport.clientHeight / 2
        );

    });

    document.getElementById('zoom-out')?.addEventListener('click', () => {

        const viewport = document.getElementById('diagram-viewport');

        zoomDiagram(
            1 / ZOOM_FACTOR,
            viewport.clientWidth / 2,
            viewport.clientHeight / 2
        );

    });

    document.getElementById('zoom-reset')?.addEventListener('click', () => {

        fitDiagramToViewport();

    });

    document.getElementById('zoom-fit')?.addEventListener('click', () => {

        fitDiagramToViewport();

    });
}


/* =========================================
   Fit Diagram to Viewport
========================================= */

function fitDiagramToViewport() {

    const viewport = document.getElementById('diagram-viewport');
    const stage = document.getElementById('diagram-stage');
    const content = document.getElementById('diagram-content');
    const svg = content?.querySelector('svg');

    if (!viewport || !stage || !content || !svg) return;

    const viewBox = svg.viewBox.baseVal;

    if (!viewBox.width || !viewBox.height) return;

    // Set SVG to natural dimensions
    svg.style.width = `${viewBox.width}px`;
    svg.style.height = `${viewBox.height}px`;

    // Remove existing transform before measuring
    content.style.transform = 'none';

    const naturalWidth = content.offsetWidth;
    const naturalHeight = content.offsetHeight;

    const availableWidth = viewport.clientWidth - (DIAGRAM_PADDING * 2);
    const availableHeight = viewport.clientHeight - (DIAGRAM_PADDING * 2);

    const scaleX = availableWidth / naturalWidth;
    const scaleY = availableHeight / naturalHeight;

    diagramFitScale = Math.min(scaleX, scaleY, 1);

    // Apply initial fit
    applyDiagramScale(diagramFitScale);

    // Reset viewport position
    viewport.scrollTop = 0;
    viewport.scrollLeft = 0;

    console.log('Diagram fitted:', {
        naturalWidth,
        naturalHeight,
        fitScale: diagramFitScale
    });
}





/* =========================================
   Render Mermaid
========================================= */

document.addEventListener('DOMContentLoaded', async () => {

    const diagram = document.querySelector(
        '#diagram-content .mermaid'
    );

    if (!diagram) return;

    try {

        await mermaid.run({
            nodes: [diagram]
        });

        const svg = diagram.querySelector('svg');

        if (svg) {

            const viewBox = svg.viewBox.baseVal;

            svg.style.width = `${viewBox.width}px`;
            svg.style.height = `${viewBox.height}px`;

        }

        styleMermaidDiagram();

        fitDiagramToViewport();

        setupDiagramControls();
        setupZoomButtons();

        diagram.classList.add('rendered');

    } catch (error) {

        console.error('Mermaid rendering failed:', error);

        diagram.textContent = 'Unable to render database diagram.';
        diagram.classList.add('rendered');

    }

});



window.addEventListener('resize', () => {
    fitDiagramToViewport();
});