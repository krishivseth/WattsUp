/**
 * Google Maps Crime Heatmap Component - Adapted from safe-route
 * Integrates real-time NYC crime data visualization with Google Maps route planning
 */

class GoogleMapsCrimeHeatmap {
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
        this.isVisible = true;
        
        // Initialize the heatmap
        this.initialize();
    }
    
    initialize() {
        // Create UI elements
        this.createUIElements();
        
        // Load crime data
        this.loadCrimeData();
    }
    
    createUIElements() {
        // Create loading indicator
        this.loadingElement = document.createElement('div');
        this.loadingElement.className = 'crime-heatmap-loading';
        this.loadingElement.innerHTML = `
            <div style="background: rgba(255, 255, 255, 0.95); border-radius: 12px; padding: 16px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15); font-size: 14px;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <div style="width: 16px; height: 16px; border: 2px solid #3b82f6; border-top-color: transparent; border-radius: 50%; animation: spin 1s linear infinite;"></div>
                    <span>Loading crime data...</span>
                </div>
            </div>
        `;
        this.loadingElement.style.cssText = `
            position: absolute;
            top: 80px;
            left: 20px;
            z-index: 1000;
            display: none;
        `;
        
        // Create error indicator
        this.errorElement = document.createElement('div');
        this.errorElement.className = 'crime-heatmap-error';
        this.errorElement.style.cssText = `
            position: absolute;
            top: 80px;
            left: 20px;
            z-index: 1000;
            display: none;
        `;
        
        // Create legend/control panel
        this.legendElement = document.createElement('div');
        this.legendElement.className = 'crime-heatmap-legend';
        this.legendElement.innerHTML = `
            <div style="background: rgba(255, 255, 255, 0.95); border-radius: 12px; padding: 16px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15); font-size: 14px; width: 220px;">
                <div style="display: flex; justify-content: between; align-items: center; margin-bottom: 12px;">
                    <h3 style="font-weight: 600; margin: 0; color: #1f2937;">🔍 Crime Density</h3>
                    <button id="toggleHeatmap" style="padding: 4px 8px; background: #ef4444; color: white; border: none; border-radius: 6px; font-size: 11px; cursor: pointer; transition: background-color 0.2s;">
                        Hide
                    </button>
                </div>
                <div style="display: grid; gap: 6px; margin-bottom: 12px;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <div style="width: 16px; height: 12px; background: linear-gradient(90deg, rgba(0,255,0,0.6), rgba(255,255,0,0.6)); border-radius: 2px;"></div>
                        <span style="font-size: 11px; color: #6b7280;">Low Risk</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <div style="width: 16px; height: 12px; background: linear-gradient(90deg, rgba(255,255,0,0.6), rgba(255,165,0,0.6)); border-radius: 2px;"></div>
                        <span style="font-size: 11px; color: #6b7280;">Medium Risk</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <div style="width: 16px; height: 12px; background: linear-gradient(90deg, rgba(255,165,0,0.6), rgba(255,0,0,0.8)); border-radius: 2px;"></div>
                        <span style="font-size: 11px; color: #6b7280;">High Risk</span>
                    </div>
                </div>
                <div style="padding-top: 12px; border-top: 1px solid #e5e7eb;">
                    <p style="font-size: 11px; color: #6b7280; margin: 0;">
                        <span id="crimeCount">0</span> recent incidents loaded
                    </p>
                    <div style="font-size: 10px; color: #9ca3af; margin-top: 4px;">
                        Data from NYC Open Data
                    </div>
                </div>
            </div>
        `;
        this.legendElement.style.cssText = `
            position: absolute;
            bottom: 120px;
            left: 20px;
            z-index: 1000;
            display: none;
        `;
        
        // Add CSS animation for loading spinner
        const style = document.createElement('style');
        style.textContent = `
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
        `;
        document.head.appendChild(style);
        
        // Add elements to map container
        const mapContainer = this.map.getDiv().parentElement;
        mapContainer.appendChild(this.loadingElement);
        mapContainer.appendChild(this.errorElement);
        mapContainer.appendChild(this.legendElement);
        
        // Set up event listeners
        this.setupEventListeners();
    }
    
    setupEventListeners() {
        // Toggle heatmap visibility
        const toggleButton = this.legendElement.querySelector('#toggleHeatmap');
        toggleButton.addEventListener('click', () => {
            this.toggleHeatmap();
        });
    }
    
    async loadCrimeData() {
        this.showLoading(true);
        this.error = null;
        
        try {
            // Load crime data from NYC Open Data API
            const response = await fetch('https://data.cityofnewyork.us/resource/qgea-i56i.json?' + new URLSearchParams({
                '$where': 'latitude IS NOT NULL AND longitude IS NOT NULL',
                '$select': 'latitude,longitude,ofns_desc,cmplnt_fr_dt,boro_nm',
                '$limit': '15000',
                '$order': 'cmplnt_fr_dt DESC'
            }));
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            this.crimeData = await response.json();
            this.crimeCount = this.crimeData.length;
            console.log(`Loaded ${this.crimeCount} crime incidents for heatmap`);
            
            // Create heatmap
            this.createHeatmap();
            
            // Update UI
            this.updateCrimeCount();
            this.showLegend();
            
        } catch (error) {
            console.error('Error fetching crime data:', error);
            this.error = 'Failed to load crime data. The heatmap will not be available.';
            this.showError(this.error);
        } finally {
            this.showLoading(false);
        }
    }
    
    createHeatmap() {
        if (!this.crimeData.length) return;
        
        // Process crime data into Google Maps heatmap format
        const heatmapData = this.crimeData.map(crime => {
            const lat = parseFloat(crime.latitude);
            const lng = parseFloat(crime.longitude);
            
            if (isNaN(lat) || isNaN(lng)) return null;
            
            // Weight by crime severity (safe-route's approach)
            const crimeType = (crime.ofns_desc || '').toLowerCase();
            let weight = 1;
            
            if (crimeType.includes('assault') || crimeType.includes('robbery') || 
                crimeType.includes('rape') || crimeType.includes('murder')) {
                weight = 3; // High severity
            } else if (crimeType.includes('burglary') || crimeType.includes('theft') || 
                       crimeType.includes('larceny')) {
                weight = 2; // Medium severity
            }
            
            return {
                location: new google.maps.LatLng(lat, lng),
                weight: weight
            };
        }).filter(point => point !== null);
        
        // Create Google Maps heatmap layer
        this.heatmapLayer = new google.maps.visualization.HeatmapLayer({
            data: heatmapData,
            map: this.map,
            radius: 25,
            opacity: 0.7,
            maxIntensity: 5,
            gradient: [
                'rgba(0, 255, 255, 0)',
                'rgba(0, 255, 255, 1)',
                'rgba(0, 191, 255, 1)',
                'rgba(0, 127, 255, 1)',
                'rgba(0, 63, 255, 1)',
                'rgba(0, 0, 255, 1)',
                'rgba(0, 0, 223, 1)',
                'rgba(0, 0, 191, 1)',
                'rgba(0, 0, 159, 1)',
                'rgba(0, 0, 127, 1)',
                'rgba(63, 0, 91, 1)',
                'rgba(127, 0, 63, 1)',
                'rgba(191, 0, 31, 1)',
                'rgba(255, 0, 0, 1)'
            ]
        });
        
        console.log(`Crime heatmap created with ${heatmapData.length} data points`);
    }
    
    toggleHeatmap() {
        if (!this.heatmapLayer) return;
        
        const toggleButton = this.legendElement.querySelector('#toggleHeatmap');
        
        if (this.isVisible) {
            this.heatmapLayer.setMap(null);
            toggleButton.textContent = 'Show';
            toggleButton.style.background = '#10b981';
            this.isVisible = false;
        } else {
            this.heatmapLayer.setMap(this.map);
            toggleButton.textContent = 'Hide';
            toggleButton.style.background = '#ef4444';
            this.isVisible = true;
        }
    }
    
    showLoading(show) {
        this.isLoading = show;
        this.loadingElement.style.display = show ? 'block' : 'none';
    }
    
    showError(message) {
        this.errorElement.innerHTML = `
            <div style="background: rgba(255, 255, 255, 0.95); border-radius: 12px; padding: 16px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15); font-size: 14px; max-width: 300px;">
                <div style="display: flex; align-items: center; gap: 8px; color: #dc2626;">
                    <span>⚠️</span>
                    <span>${message}</span>
                </div>
            </div>
        `;
        this.errorElement.style.display = 'block';
        
        // Hide error after 7 seconds
        setTimeout(() => {
            this.errorElement.style.display = 'none';
        }, 7000);
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
    getCrimeDensity(lat, lng, radius = 0.003) {
        if (!this.crimeData.length) return 0;
        
        let totalWeight = 0;
        
        for (const crime of this.crimeData) {
            try {
                const crimeLat = parseFloat(crime.latitude);
                const crimeLng = parseFloat(crime.longitude);
                
                if (isNaN(crimeLat) || isNaN(crimeLng)) continue;
                
                const dLat = crimeLat - lat;
                const dLng = crimeLng - lng;
                const distance = Math.sqrt(dLat * dLat + dLng * dLng);
                
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
    
    // Get high-risk areas along a route
    getHighRiskAreas(routeCoordinates, threshold = 15) {
        const highRiskAreas = [];
        
        if (!this.crimeData.length || !routeCoordinates) return highRiskAreas;
        
        // Sample points along the route
        const sampleRate = Math.max(1, Math.floor(routeCoordinates.length / 20)); // Sample ~20 points
        
        for (let i = 0; i < routeCoordinates.length; i += sampleRate) {
            const coord = routeCoordinates[i];
            const density = this.getCrimeDensity(coord.lat, coord.lng);
            
            if (density > threshold) {
                highRiskAreas.push({
                    lat: coord.lat,
                    lng: coord.lng,
                    density: density,
                    riskLevel: density > 25 ? 'high' : 'medium',
                    description: `${Math.round(density)} incidents in nearby area`
                });
            }
        }
        
        return highRiskAreas;
    }
    
    // Clean up when component is destroyed
    destroy() {
        if (this.heatmapLayer) {
            this.heatmapLayer.setMap(null);
        }
        
        // Remove UI elements
        if (this.loadingElement) this.loadingElement.remove();
        if (this.errorElement) this.errorElement.remove();
        if (this.legendElement) this.legendElement.remove();
    }
}

// Export for global use
window.GoogleMapsCrimeHeatmap = GoogleMapsCrimeHeatmap; 