/**
 * Visualization Module for Yieldera Dashboard
 * Handles predefined region selection and analysis generation
 */

const VisualizationModule = (function () {
    // State
    const state = {
        regions: [],
        selectedCategory: '',
        selectedRegionId: null,
        status: 'idle', // idle, polling, completed, failed
        jobId: null,
        currentImage: null
    };

    // DOM Elements
    const elements = {
        container: null,
        regionCategory: null,
        specificRegionGroup: null,
        specificRegion: null,
        baselinePeriod: null,
        customBaselineGroup: null,
        generateBtn: null,

        resultsPanel: null,
        progressPanel: null,

        // Modal Elements
        resultModal: null,
        resultModalContent: null,
        closeModalBtn: null,
        modalBackdrop: null
    };

    // API Configuration
    // API Configuration
    const API_BASE = `${CONFIG.API_BASE_URL}/api/v1/visualization`;

    // Initialize Module
    function init() {
        console.log('Initializing Visualization Module...');
        console.log('API Base URL:', API_BASE);
        cacheDOM();
        bindEvents();
        fetchRegions();

        // Hide initial loading overlay since main.js is not present
        if (window.Utils && window.Utils.hideLoadingOverlay) {
            setTimeout(() => window.Utils.hideLoadingOverlay(), 500);
        } else {
            const overlay = document.getElementById('loadingOverlay');
            if (overlay) overlay.style.display = 'none';
        }
    }

    function cacheDOM() {
        elements.container = document.querySelector('.visualization-module-container');
        if (!elements.container) return; // Module not present in current view

        elements.regionCategory = document.getElementById('regionCategory');
        elements.specificRegionGroup = document.getElementById('specificRegionGroup');
        elements.specificRegion = document.getElementById('specificRegion');

        elements.baselinePeriod = document.getElementById('baselinePeriod');
        elements.customBaselineGroup = document.getElementById('customBaselineGroup');

        elements.generateBtn = document.getElementById('generateVisualization');

        // Modal Elements
        elements.resultModal = document.getElementById('resultModal');
        elements.resultModalContent = document.getElementById('resultModalContent');
        elements.closeModalBtn = document.getElementById('closeModalBtn');
        elements.modalBackdrop = document.getElementById('modalBackdrop');

        elements.progressPanel = document.getElementById('progressPanel');
        elements.errorPanel = document.getElementById('errorPanel');
    }

    function bindEvents() {
        if (!elements.container) return;

        // Category Change
        elements.regionCategory.addEventListener('change', (e) => {
            handleCategoryChange(e.target.value);
        });

        // Baseline Period Change
        elements.baselinePeriod.addEventListener('change', (e) => {
            if (e.target.value === 'custom') {
                elements.customBaselineGroup.style.display = 'block';
            } else {
                elements.customBaselineGroup.style.display = 'none';
            }
        });

        // Generate Button
        elements.generateBtn.addEventListener('click', handleGenerate);

        // Modal Events
        if (elements.closeModalBtn) {
            elements.closeModalBtn.addEventListener('click', closeModal);
        }
        if (elements.modalBackdrop) {
            elements.modalBackdrop.addEventListener('click', closeModal);
        }
    }

    async function fetchRegions() {
        try {
            const response = await fetch(`${API_BASE}/regions`);
            if (!response.ok) throw new Error('Failed to load regions');
            state.regions = await response.json();
            console.log('Regions loaded:', state.regions);
        } catch (error) {
            console.error('Error fetching regions:', error);
            showError('Failed to load region data. Please refresh page.');
        }
    }

    function handleCategoryChange(category) {
        state.selectedCategory = category;
        elements.specificRegion.innerHTML = '<option value="">Select Specific Region</option>';

        if (!category) {
            elements.specificRegionGroup.style.display = 'none';
            return;
        }

        const filteredRegions = state.regions.filter(r => r.category === category);

        if (filteredRegions.length > 0) {
            filteredRegions.forEach(region => {
                const option = document.createElement('option');
                option.value = region.id;
                option.textContent = region.name;
                elements.specificRegion.appendChild(option);
            });
            elements.specificRegionGroup.style.display = 'block';
        } else {
            elements.specificRegionGroup.style.display = 'none';
        }
    }

    async function handleGenerate() {
        // Validation
        const regionId = elements.specificRegion.value;
        const category = elements.regionCategory.value;
        const start = document.getElementById('analysisStart').value;
        const end = document.getElementById('analysisEnd').value;
        const analysisType = document.getElementById('analysisType').value;
        const regionName = elements.specificRegion.options[elements.specificRegion.selectedIndex]?.text || "Selected Region";

        if (!regionId && category !== 'country') {
            // Note: 'country' often implies the single country option if not filtered, but here country is a category containing 'Zimbabwe'
            // logic adjustment: if category has children, must select child.
        }

        if (!regionId) {
            alert('Please select a specific region.');
            return;
        }

        if (!start || !end) {
            alert('Please select analysis dates.');
            return;
        }

        // Prepare Payload
        const payload = {
            region_name: regionName,
            region_id: regionId,
            region_type: category, // province, district
            start_date: start,
            end_date: end,
            analysis_type: analysisType,
            baseline_type: elements.baselinePeriod.value
        };

        if (payload.baseline_type === 'custom') {
            payload.baseline_config = {
                start_date: document.getElementById('baselineStart').value,
                end_date: document.getElementById('baselineEnd').value
            };
        }

        // Start Job
        resetUI();
        showProgress(true, 'Starting analysis...');

        try {
            const response = await fetch(`${API_BASE}/generate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || 'Analysis failed to start');
            }

            const data = await response.json();
            state.jobId = data.job_id;
            state.status = 'polling';
            pollStatus();

        } catch (error) {
            console.error(error);
            showError(error.message);
            showProgress(false);
        }
    }

    function pollStatus() {
        if (state.status !== 'polling') return;

        const interval = setInterval(async () => {
            try {
                const response = await fetch(`${API_BASE}/jobs/${state.jobId}/status`);
                const data = await response.json();

                updateProgress(data.progress, data.message);

                if (data.status === 'completed') {
                    clearInterval(interval);
                    state.status = 'completed';
                    fetchResults(state.jobId);
                } else if (data.status === 'failed') {
                    clearInterval(interval);
                    state.status = 'failed';
                    showError(data.message || 'Analysis failed.');
                    showProgress(false); // Hide progress bar
                }
            } catch (e) {
                console.error('Polling error', e);
            }
        }, 2000);
    }

    async function fetchResults(jobId) {
        try {
            const response = await fetch(`${API_BASE}/jobs/${jobId}/preview`);
            const data = await response.json();
            renderResults(data);
            showProgress(false);
        } catch (e) {
            showError('Failed to load results.');
        }
    }

    function downloadImage() {
        if (!state.currentImage) return;
        const link = document.createElement('a');
        link.href = `data:image/png;base64,${state.currentImage}`;
        link.download = `yieldera_analysis_${state.jobId || new Date().toISOString().slice(0, 10)}.png`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    function renderResults(data) {
        state.currentImage = data.image_data;

        elements.resultModalContent.innerHTML = `
            <div class="result-card bg-transparent">
                <div class="p-0">
                    <img src="data:image/png;base64,${data.image_data}" class="w-full h-auto object-contain rounded mb-6 shadow-sm" style="max-height: none;" />
                    
                    <div class="stats-grid grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                        <div class="stat-box p-4 bg-white dark:bg-secondary rounded border border-gray-200 dark:border-gray-600">
                            <div class="text-xs text-gray-500 uppercase tracking-wide">Mean Anomaly</div>
                            <div class="text-2xl font-bold">${data.statistics?.mean_anomaly?.toFixed(3) || 'N/A'}</div>
                        </div>
                         <div class="stat-box p-4 bg-white dark:bg-secondary rounded border border-gray-200 dark:border-gray-600">
                            <div class="text-xs text-gray-500 uppercase tracking-wide">Max Anomaly</div>
                            <div class="text-2xl font-bold">${data.statistics?.max_anomaly?.toFixed(3) || 'N/A'}</div>
                        </div>
                    </div>

                    <div class="flex gap-4 justify-center">
                        <button class="w-full md:w-auto px-8 bg-primary text-secondary py-3 rounded-lg hover:bg-primary-light transition font-bold shadow-lg transform hover:scale-105" onclick="VisualizationModule.downloadImage()">
                            <i class="fas fa-download mr-2"></i> Download Full Resolution Map
                        </button>
                    </div>
                </div>
            </div>
        `;

        showModal();
    }

    // Export Helper (Public)
    function exportMap(format) {
        if (!state.jobId) return;

        // Use a hidden form or fetch blob to download
        fetch(`${API_BASE}/export`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ job_id: state.jobId, format: format })
        })
            .then(response => response.blob())
            .then(blob => {
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `analysis_${state.jobId}.${format}`;
                document.body.appendChild(a);
                a.click();
                a.remove();
            });
    }

    // UI Helpers
    function resetUI() {
        // elements.resultsPanel.style.display = 'none'; // Removed inline panel
        // if (elements.vizEmptyState) elements.vizEmptyState.style.display = 'flex';
        closeModal();
        elements.errorPanel.style.display = 'none';
    }

    function showProgress(show, message) {
        elements.progressPanel.style.display = show ? 'block' : 'none';
        if (show && message) {
            elements.progressPanel.querySelector('.progress-message').textContent = message;
        }
    }

    function updateProgress(percent, message) {
        const bar = elements.progressPanel.querySelector('.progress-bar-fill');
        const text = elements.progressPanel.querySelector('.progress-message');
        if (bar) bar.style.width = `${percent}%`;
        if (text) text.textContent = `${percent}% - ${message}`;
    }

    function showError(msg) {
        elements.errorPanel.textContent = msg;
        elements.errorPanel.style.display = 'block';
    }

    // Modal Helpers
    function showModal() {
        elements.resultModal.classList.remove('hidden');
        document.body.style.overflow = 'hidden'; // Prevent background scrolling
    }

    function closeModal() {
        elements.resultModal.classList.add('hidden');
        document.body.style.overflow = ''; // Restore scrolling
    }

    // Public API
    return {
        init: init,
        exportMap: exportMap,
        downloadImage: downloadImage
    };
})();

// Auto-init if DOM is ready, or wait
document.addEventListener('DOMContentLoaded', () => {
    // Only init if we are on the page with the container
    if (document.querySelector('.visualization-module-container')) {
        VisualizationModule.init();
    }
});
