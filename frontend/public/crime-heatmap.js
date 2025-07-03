/**
 * Crime Heatmap Component - Adapted from safe-route
 * Integrates real-time NYC crime data visualization with route planning
 */

class CrimeHeatmap {
    constructor(map) {
        this.map = map;
        this.heatmapLayer = null;
        this.crimeData = [];
        this.isLoading = false;
        this.error = null;
        this.crimeCount = 0;
        this.legendElement = null;
        this.loadingElement = null;
        this.errorElement = null;
        
        // Initialize the heatmap
        this.initialize();
    }
    
    initialize() {
        // Create UI elements
        this.createUIElements();
        
        // Load crime data
        this.loadCrimeData();
        
        // Set up event listeners
        this.setupEventListeners();
    }
    
    createUIElements() {
        // Create loading indicator
        this.loadingElement = document.createElement('div');
        this.loadingElement.className = 'crime-heatmap-loading';
        this.loadingElement.innerHTML = `
            <div class="glass-effect rounded-xl p-4 text-sm">
                <div class="flex items-center gap-2">
                    <div class="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
                    <span>Loading crime data...</span>
                </div>
            </div>
        `;
        this.loadingElement.style.cssText = `
            position: absolute;
            top: 20px;
            left: 20px;
            z-index: 1000;
            background: rgba(255, 255, 255, 0.9);
            backdrop-filter: blur(10px);
            border-radius: 12px;
            padding: 16px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            display: none;
        `;
        
        // Create error indicator
        this.errorElement = document.createElement('div');
        this.errorElement.className = 'crime-heatmap-error';
        this.errorElement.style.cssText = `
            position: absolute;
            top: 20px;
            left: 20px;
            z-index: 1000;
            background: rgba(255, 255, 255, 0.9);
            backdrop-filter: blur(10px);
            border-radius: 12px;
            padding: 16px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            display: none;
        `;
        
        // Create legend
        this.legendElement = document.createElement('div');
        this.legendElement.className = 'crime-heatmap-legend';
        this.legendElement.innerHTML = `
            <div class="glass-effect rounded-xl p-4 text-sm">
                <h3 class="font-semibold mb-3 text-gray-800">Crime Density</h3>
                <div class="grid gap-2">
                    <div class="flex items-center gap-2">
                        <div class="w-4 h-4 rounded" style="background: rgba(44, 123, 182, 0.3);"></div>
                        <span class="text-xs text-gray-700">Low</span>
                    </div>
                    <div class="flex items-center gap-2">
                        <div class="w-4 h-4 rounded" style="background: rgba(0, 166, 202, 0.4);"></div>
                        <span class="text-xs text-gray-700">Medium-Low</span>
                    </div>
                    <div class="flex items-center gap-2">
                        <div class="w-4 h-4 rounded" style="background: rgba(127, 188, 65, 0.5);"></div>
                        <span class="text-xs text-gray-700">Medium</span>
                    </div>
                    <div class="flex items-center gap-2">
                        <div class="w-4 h-4 rounded" style="background: rgba(244, 165, 130, 0.6);"></div>
                        <span class="text-xs text-gray-700">Medium-High</span>
                    </div>
                    <div class="flex items-center gap-2">
                        <div class="w-4 h-4 rounded" style="background: rgba(215, 25, 28, 0.7);"></div>
                        <span class="text-xs text-gray-700">High</span>
                    </div>
                </div>
                <div class="mt-3 pt-3 border-t border-gray-200">
                    <p class="text-xs text-gray-600">
                        <span id="crimeCount">0</span> recent incidents
                    </p>
                    <button id="toggleHeatmap" class="mt-2 px-3 py-1 bg-blue-600 text-white rounded-lg text-xs hover:bg-blue-700 transition-colors">
                        Hide Heatmap
                    </button>
                </div>
            </div>
        `;
        this.legendElement.style.cssText = `
            position: absolute;
            bottom: 20px;
            left: 20px;
            z-index: 1000;
            background: rgba(255, 255, 255, 0.9);
            backdrop-filter: blur(10px);
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            display: none;
        `;
        
        // Add elements to map container
        const mapContainer = this.map.getContainer();
        mapContainer.appendChild(this.loadingElement);
        mapContainer.appendChild(this.errorElement);
        mapContainer.appendChild(this.legendElement);
    }
    
    setupEventListeners() {
        // Toggle heatmap visibility
        const toggleButton = this.legendElement.querySelector('#toggleHeatmap');
        toggleButton.addEventListener('click', () => {
            this.toggleHeatmap();
        });
        
        // Update heatmap on zoom/pan
        this.map.on('zoomend', () => this.updateHeatmap());
        this.map.on('moveend', () => this.updateHeatmap());
    }
    
    async loadCrimeData() {
        this.showLoading(true);
        this.error = null;
        
        try {
            const response = await fetch('https://data.cityofnewyork.us/resource/qgea-i56i.json?' + new URLSearchParams({
                '$where': 'latitude IS NOT NULL AND longitude IS NOT NULL',
                '$select': 'latitude,longitude,ofns_desc,cmplnt_fr_dt,boro_nm',
                '$limit': '10000',
                '$order': 'cmplnt_fr_dt DESC'
            }));
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            this.crimeData = await response.json();
            this.crimeCount = this.crimeData.length;
            
            // Create heatmap
            this.createHeatmap();
            
            // Update UI
            this.updateCrimeCount();
            this.showLegend();
            
        } catch (error) {
            console.error('Error fetching crime data:', error);
            this.error = 'Failed to load crime data. Please try again later.';
            this.showError(this.error);
        } finally {
            this.showLoading(false);
        }
    }
    
    createHeatmap() {
        if (!this.crimeData.length) return;
        
        // Process crime data into heatmap points
        const heatPoints = this.crimeData.map(crime => {
            let intensity = 0.6;
            const crimeType = (crime.ofns_desc || '').toLowerCase();
            
            // Weight by crime severity (safe-route's approach)
            if (crimeType.includes('assault') || crimeType.includes('robbery') || 
                crimeType.includes('rape') || crimeType.includes('murder')) {
                intensity = 1.0;
            } else if (crimeType.includes('burglary') || crimeType.includes('theft') || 
                       crimeType.includes('larceny')) {
                intensity = 0.8;
            }
            
            return [
                parseFloat(crime.latitude),
                parseFloat(crime.longitude),
                intensity
            ];
        }).filter(point => !isNaN(point[0]) && !isNaN(point[1]));
        
        // Create heatmap layer
        this.heatmapLayer = L.heatLayer(heatPoints, {
            radius: this.getRadius(this.map.getZoom()),
            blur: 2,
            maxZoom: 18,
            max: 1.0,
            gradient: {
                0.2: 'rgba(44, 123, 182, 0.3)',
                0.4: 'rgba(0, 166, 202, 0.4)',
                0.6: 'rgba(127, 188, 65, 0.5)',
                0.8: 'rgba(244, 165, 130, 0.6)',
                1.0: 'rgba(215, 25, 28, 0.7)'
            },
            minOpacity: 0.2
        });
        
        // Add to map
        this.heatmapLayer.addTo(this.map);
    }
    
    getRadius(zoom) {
        // Scale radius with zoom level
        return Math.max(10, 2 * Math.pow(2, zoom - 12));
    }
    
    updateHeatmap() {
        if (this.heatmapLayer) {
            this.heatmapLayer.setOptions({
                radius: this.getRadius(this.map.getZoom()),
                blur: 2
            });
            this.heatmapLayer.redraw();
        }
    }
    
    toggleHeatmap() {
        if (!this.heatmapLayer) return;
        
        const toggleButton = this.legendElement.querySelector('#toggleHeatmap');
        
        if (this.map.hasLayer(this.heatmapLayer)) {
            this.map.removeLayer(this.heatmapLayer);
            toggleButton.textContent = 'Show Heatmap';
            toggleButton.classList.remove('bg-blue-600', 'hover:bg-blue-700');
            toggleButton.classList.add('bg-green-600', 'hover:bg-green-700');
        } else {
            this.map.addLayer(this.heatmapLayer);
            toggleButton.textContent = 'Hide Heatmap';
            toggleButton.classList.remove('bg-green-600', 'hover:bg-green-700');
            toggleButton.classList.add('bg-blue-600', 'hover:bg-blue-700');
        }
    }
    
    showLoading(show) {
        this.isLoading = show;
        this.loadingElement.style.display = show ? 'block' : 'none';
    }
    
    showError(message) {
        this.errorElement.innerHTML = `
            <div class="glass-effect rounded-xl p-4 text-sm">
                <div class="flex items-center gap-2 text-red-600">
                    <span>⚠️</span>
                    <span>${message}</span>
                </div>
            </div>
        `;
        this.errorElement.style.display = 'block';
        
        // Hide error after 5 seconds
        setTimeout(() => {
            this.errorElement.style.display = 'none';
        }, 5000);
    }
    
    showLegend() {
        this.legendElement.style.display = 'block';
    }
    
    hideLegend() {
        this.legendElement.style.display = 'none';
    }
    
    updateCrimeCount() {
        const countElement = this.legendElement.querySelector('#crimeCount');
        if (countElement) {
            countElement.textContent = this.crimeCount.toLocaleString();
        }
    }
    
    // Public method to get crime density at a specific location
    getCrimeDensity(lat, lon, radius = 0.003) {
        if (!this.crimeData.length) return 0;
        
        let totalWeight = 0;
        
        for (const crime of this.crimeData) {
            try {
                const crimeLat = parseFloat(crime.latitude);
                const crimeLon = parseFloat(crime.longitude);
                
                const dLat = crimeLat - lat;
                const dLon = crimeLon - lon;
                const distance = Math.sqrt(dLat * dLat + dLon * dLon);
                
                if (distance <= radius) {
                    const crimeDesc = (crime.ofns_desc || '').toLowerCase();
                    let weight = 1;
                    
                    if (crimeDesc.includes('assault') || crimeDesc.includes('robbery') || 
                        crimeDesc.includes('rape') || crimeDesc.includes('murder')) {
                        weight = 8;
                    } else if (crimeDesc.includes('burglary') || crimeDesc.includes('theft') || 
                               crimeDesc.includes('larceny')) {
                        weight = 5;
                    }
                    
                    totalWeight += weight;
                }
            } catch (e) {
                continue;
            }
        }
        
        return totalWeight;
    }
    
    // Clean up when component is destroyed
    destroy() {
        if (this.heatmapLayer) {
            this.map.removeLayer(this.heatmapLayer);
        }
        
        // Remove UI elements
        if (this.loadingElement) this.loadingElement.remove();
        if (this.errorElement) this.errorElement.remove();
        if (this.legendElement) this.legendElement.remove();
        
        // Remove event listeners
        this.map.off('zoomend');
        this.map.off('moveend');
    }
}

// Export for global use
window.CrimeHeatmap = CrimeHeatmap; 