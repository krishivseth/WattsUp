// Enhanced Global Variables
let map;
let directionsService;
let directionsRenderers = [];
let routeData = [];
let selectedRouteIndex = 0;
let trafficLayer;
let bounds;
let crimeHeatmap;

// Initialize the application with enhanced loading
async function initializeRoutePlanner() {
    try {
        updateLoadingStatus('Initializing application...');
        
        // Get URL parameters
        const urlParams = new URLSearchParams(window.location.search);
        const origin = urlParams.get('origin');
        const destination = urlParams.get('destination');
        
        // Debug logging
        console.log('Route Planner Debug:', {
            fullURL: window.location.href,
            origin: origin,
            destination: destination,
            allParams: Object.fromEntries(urlParams)
        });

        if (!origin || !destination) {
            throw new Error('Origin and destination addresses are required');
        }
        
        // Check if destination looks invalid
        if (destination.length < 5 || destination.match(/^view\s*\d+$/i)) {
            throw new Error(`Invalid destination address: "${destination}". Please enter a real address like "Times Square, NYC" or "Brooklyn Bridge, NY".`);
        }

        // Display addresses
        document.getElementById('originDisplay').textContent = origin;
        document.getElementById('destinationDisplay').textContent = destination;
        document.getElementById('routeSummary').classList.remove('hidden');
        document.getElementById('progressContainer').classList.remove('hidden');

        updateLoadingStatus('Initializing map...');
        await initializeMap();

        updateLoadingStatus('Analyzing safe routes...');
        await analyzeRoutes(origin, destination);

    } catch (error) {
        console.error('Route planner initialization failed:', error);
        showError(error.message);
    }
}

function updateLoadingStatus(message) {
    const progressEl = document.getElementById('loadingProgress');
    progressEl.innerHTML = `
        <div class="flex items-center justify-center gap-2 text-sm text-gray-500">
            <span class="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></span>
            <span>${message}</span>
        </div>
    `;
}

async function initializeMap() {
    return new Promise((resolve) => {
        const mapOptions = {
            zoom: 12,
            center: { lat: 40.7589, lng: -73.9851 }, // NYC center
            styles: [
                {
                    "featureType": "all",
                    "elementType": "geometry.fill",
                    "stylers": [{"weight": "2.00"}]
                },
                {
                    "featureType": "all",
                    "elementType": "geometry.stroke",
                    "stylers": [{"color": "#9c9c9c"}]
                },
                {
                    "featureType": "all",
                    "elementType": "labels.text",
                    "stylers": [{"visibility": "on"}]
                }
            ],
            mapTypeControl: false,
            streetViewControl: false,
            fullscreenControl: true,
            zoomControl: true,
            gestureHandling: 'greedy'
        };

        map = new google.maps.Map(document.getElementById('map'), mapOptions);
        directionsService = new google.maps.DirectionsService();
        trafficLayer = new google.maps.TrafficLayer();
        bounds = new google.maps.LatLngBounds();
        
        // Initialize crime heatmap overlay
        if (window.GoogleMapsCrimeHeatmap) {
            try {
                crimeHeatmap = new GoogleMapsCrimeHeatmap(map);
                console.log('Crime heatmap initialized successfully');
            } catch (error) {
                console.warn('Failed to initialize crime heatmap:', error);
            }
        }
        
        resolve();
    });
}

async function analyzeRoutes(origin, destination) {
    try {
        const requestData = {
            origin: origin,
            destination: destination,
            mode: 'driving',
            alternatives: true
        };
        
        console.log('Making API request:', requestData);
        
        const response = await fetch('http://127.0.0.1:56834/api/safe-routes', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestData),
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `API request failed with status ${response.status}`);
        }

        const data = await response.json();
        
        if (data.error) {
            throw new Error(data.error);
        }
        
        routeData = data.routes || [];

        if (routeData.length === 0) {
            throw new Error('No safe routes found for this destination. Please try a different location.');
        }

        // Hide loading and progress
        document.getElementById('loadingState').classList.add('hidden');
        document.getElementById('progressContainer').classList.add('hidden');
        
        // Display results
        displayRouteCards(data);
        await displayRoutesOnMap(origin, destination);
        updateRouteStats();
        
        // Show side panel
        document.getElementById('sidePanel').classList.remove('hidden');

    } catch (error) {
        console.error('Route analysis error:', error);
        throw new Error(`Failed to analyze routes: ${error.message}`);
    }
}

function displayRouteCards(data) {
    const container = document.getElementById('routeCards');
    container.innerHTML = '';

    // Categorize routes based on their characteristics
    categorizeRoutes();

    routeData.forEach((route, index) => {
        const card = createRouteCard(route, index);
        container.appendChild(card);
    });

    // Show recommendation
    if (data.recommendation && data.recommendation.reason) {
        const recCard = document.getElementById('recommendationCard');
        document.getElementById('recommendationText').textContent = data.recommendation.reason;
        recCard.classList.remove('hidden');
    }

    // Show route stats
    document.getElementById('routeStats').classList.remove('hidden');
}

function categorizeRoutes() {
    if (routeData.length === 0) return;

    // Find the safest route (highest safety score)
    let safestIndex = 0;
    let highestSafetyScore = 0;
    
    // Find the fastest route (shortest duration)
    let fastestIndex = 0;
    let shortestDuration = Infinity;

    routeData.forEach((route, index) => {
        // Check for safest route
        const safetyScore = route.overall_safety_score || 0;
        if (safetyScore > highestSafetyScore) {
            highestSafetyScore = safetyScore;
            safestIndex = index;
        }

        // Check for fastest route
        const durationStr = route.duration || '';
        const durationMatch = durationStr.match(/(\d+)/);
        const duration = durationMatch ? parseInt(durationMatch[1]) : Infinity;
        if (duration < shortestDuration) {
            shortestDuration = duration;
            fastestIndex = index;
        }
    });

    // Assign route types
    routeData.forEach((route, index) => {
        if (index === safestIndex) {
            route.route_type = 'safest';
            route.type_label = 'Safest Route';
        } else if (index === fastestIndex && index !== safestIndex) {
            route.route_type = 'fastest';
            route.type_label = 'Fastest Route';
        } else {
            route.route_type = 'balanced';
            route.type_label = 'Alternative Route';
        }
    });
}

function createRouteCard(route, index) {
    const card = document.createElement('div');
    card.className = `route-card p-5 border border-gray-200 rounded-xl cursor-pointer route-${route.route_type} ${index === 0 ? 'selected' : ''}`;
    card.addEventListener('click', () => selectRoute(index));

    const safetyColor = getSafetyColor(route.overall_safety_score);
    const routeIcon = getRouteIcon(route.route_type);
    const safetyPercentage = route.overall_safety_score || 0;
    const highRiskCount = route.high_risk_areas ? route.high_risk_areas.length : 0;
    const crimeStats = route.crime_statistics || {};

    card.innerHTML = `
        <div class="flex items-center justify-between mb-4">
            <div class="flex items-center gap-3">
                <span class="text-2xl">${routeIcon}</span>
                <div>
                    <div class="font-bold text-gray-800">${route.type_label || `${route.route_type.charAt(0).toUpperCase() + route.route_type.slice(1)} Route`}</div>
                    <div class="text-xs text-gray-500">${route.summary || `Route ${index + 1}`}</div>
                </div>
            </div>
            <div class="px-3 py-1 rounded-full text-xs font-bold ${safetyColor}">
                ${route.overall_safety_grade} (${safetyPercentage}/100)
            </div>
        </div>
        
        <!-- Enhanced Safety Progress Bar -->
        <div class="mb-4">
            <div class="flex justify-between text-xs text-gray-600 mb-1">
                <span>Safety Score</span>
                <span>${safetyPercentage}/100</span>
            </div>
            <div class="w-full bg-gray-200 rounded-full h-2">
                <div class="h-2 rounded-full ${getSafetyBarColor(safetyPercentage)}" 
                     style="width: ${safetyPercentage}%"></div>
            </div>
        </div>
        
        <div class="grid grid-cols-2 gap-3 text-sm mb-3">
            <div class="bg-white/50 rounded-lg p-2">
                <div class="text-xs text-gray-500">Duration</div>
                <div class="font-semibold text-gray-800">${route.duration || 'N/A'}</div>
            </div>
            <div class="bg-white/50 rounded-lg p-2">
                <div class="text-xs text-gray-500">Distance</div>
                <div class="font-semibold text-gray-800">${route.distance || 'N/A'}</div>
            </div>
        </div>
        
        <!-- Crime Statistics -->
        ${Object.keys(crimeStats).length > 0 ? `
        <div class="grid grid-cols-2 gap-3 text-sm mb-3">
            <div class="bg-red-50 rounded-lg p-2">
                <div class="text-xs text-red-600">High-Risk Areas</div>
                <div class="font-semibold text-red-800">${highRiskCount}</div>
            </div>
            <div class="bg-blue-50 rounded-lg p-2">
                <div class="text-xs text-blue-600">Crime Incidents</div>
                <div class="font-semibold text-blue-800">${crimeStats.total_incidents_nearby || 0}</div>
            </div>
        </div>
        ` : ''}
        
        <div class="mt-3 text-xs text-gray-600 leading-relaxed">
            ${route.safety_details?.description || 'Advanced safety analysis completed'}
        </div>
        
        ${highRiskCount > 0 ? `
            <div class="mt-3 p-2 bg-amber-50 border border-amber-200 rounded-lg">
                <div class="flex items-center gap-2 text-xs text-amber-800">
                    <span>⚠️</span>
                    <span>${highRiskCount} high-crime area${highRiskCount !== 1 ? 's' : ''} along this route</span>
                </div>
            </div>
        ` : ''}
    `;

    return card;
}

async function displayRoutesOnMap(origin, destination) {
    // Clear existing renderers completely
    directionsRenderers.forEach(renderer => {
        try {
            renderer.setMap(null);
        } catch (e) {
            console.warn('Error clearing renderer:', e);
        }
    });
    directionsRenderers = [];
    bounds = new google.maps.LatLngBounds();

    // Create directions requests for each route but store them without displaying
    for (let i = 0; i < routeData.length; i++) {
        const route = routeData[i];
        
        const renderer = new google.maps.DirectionsRenderer({
            map: null, // Don't display initially
            routeIndex: 0,
            suppressMarkers: false,
            polylineOptions: {
                strokeColor: getRouteColor(route.route_type),
                strokeWeight: 6,
                strokeOpacity: 0.8,
                zIndex: 1000
            },
            markerOptions: {
                visible: true
            }
        });

        try {
            const result = await new Promise((resolve, reject) => {
                directionsService.route({
                    origin: origin,
                    destination: destination,
                    travelMode: google.maps.TravelMode.DRIVING,
                    provideRouteAlternatives: true,
                    optimizeWaypoints: false,
                    avoidHighways: route.route_type === 'safest',
                    avoidTolls: route.route_type === 'safest'
                }, (result, status) => {
                    if (status === 'OK') {
                        resolve(result);
                    } else {
                        reject(new Error(`Directions request failed: ${status}`));
                    }
                });
            });

            // Use the route that best matches our route type
            const routeIndex = Math.min(i, result.routes.length - 1);
            renderer.setRouteIndex(routeIndex);
            renderer.setDirections(result);
            
            // Store the renderer and route data
            directionsRenderers.push({
                renderer: renderer,
                result: result,
                routeIndex: routeIndex
            });
            
            // Extend bounds for the first route to set initial view
            if (i === 0) {
                const routeBounds = result.routes[routeIndex].bounds;
                bounds.union(routeBounds);
            }

        } catch (error) {
            console.warn(`Failed to prepare route ${i}:`, error);
            // Still add a placeholder to maintain index alignment
            directionsRenderers.push({ renderer: null, result: null, routeIndex: 0 });
        }
    }

    // Fit map to show the general area
    if (!bounds.isEmpty()) {
        map.fitBounds(bounds);
    }

    // Display only the first route initially
    selectRoute(0);
}

function selectRoute(index) {
    selectedRouteIndex = index;
    
    console.log('Selecting route:', index, 'Total routes:', directionsRenderers.length);
    
    // Update card selection
    document.querySelectorAll('.route-card').forEach((card, i) => {
        card.classList.toggle('selected', i === index);
    });

    // Clear all routes from map first
    directionsRenderers.forEach((rendererData, i) => {
        if (rendererData && rendererData.renderer) {
            try {
                rendererData.renderer.setMap(null);
            } catch (e) {
                console.warn('Error clearing renderer:', e);
            }
        }
    });

    // Display only the selected route
    const selectedRendererData = directionsRenderers[index];
    if (selectedRendererData && selectedRendererData.renderer) {
        try {
            console.log('Displaying route:', index, 'Type:', routeData[index]?.route_type);
            selectedRendererData.renderer.setMap(map);
            
            // Update the route color and style
            const route = routeData[index];
            selectedRendererData.renderer.setOptions({
                polylineOptions: {
                    strokeColor: getRouteColor(route.route_type),
                    strokeWeight: 6,
                    strokeOpacity: 0.9,
                    zIndex: 1000
                },
                markerOptions: {
                    visible: true
                }
            });
        } catch (e) {
            console.error('Error displaying selected route:', e);
        }
    } else {
        console.warn('No renderer data found for route index:', index);
    }

    updateSelectedRouteInfo(index);
}

function updateSelectedRouteInfo(index) {
    const route = routeData[index];
    const infoElement = document.getElementById('selectedRouteInfo');
    
    document.getElementById('selectedRouteIcon').textContent = getRouteIcon(route.route_type);
    document.getElementById('selectedRouteName').textContent = route.type_label || `${route.route_type.charAt(0).toUpperCase() + route.route_type.slice(1)} Route`;
    document.getElementById('selectedRouteDetails').textContent = `${route.duration || 'N/A'} • ${route.distance || 'N/A'}`;
    document.getElementById('selectedRouteSafety').textContent = `Grade ${route.overall_safety_grade}`;
    
    infoElement.classList.remove('hidden');
}

function updateRouteStats() {
    const totalRoutes = routeData.length;
    const avgSafety = routeData.reduce((sum, route) => sum + route.overall_safety_score, 0) / totalRoutes;
    
    // Extract duration numbers from strings like "10 mins"
    const durations = routeData.map(route => {
        const durationStr = route.duration || '';
        const match = durationStr.match(/(\d+)/);
        return match ? parseInt(match[1]) : 0;
    }).filter(d => d > 0);
    
    const timeRange = durations.length > 0 ? `${Math.min(...durations)}-${Math.max(...durations)}min` : 'N/A';
    
    document.getElementById('totalRoutes').textContent = totalRoutes;
    document.getElementById('avgSafety').textContent = avgSafety.toFixed(1);
    document.getElementById('timeRange').textContent = timeRange;
}

function recenterMap() {
    if (!bounds.isEmpty()) {
        map.fitBounds(bounds);
    }
}

function toggleTraffic() {
    if (trafficLayer.getMap()) {
        trafficLayer.setMap(null);
        const btn = document.getElementById('toggleTrafficBtn');
        if (btn) btn.style.background = 'white';
    } else {
        trafficLayer.setMap(map);
        const btn = document.getElementById('toggleTrafficBtn');
        if (btn) btn.style.background = '#e5f3ff';
    }
}

function getSafetyColor(score) {
    if (score >= 90) return 'bg-green-100 text-green-800 border border-green-200';
    if (score >= 80) return 'bg-lime-100 text-lime-800 border border-lime-200';
    if (score >= 70) return 'bg-yellow-100 text-yellow-800 border border-yellow-200';
    if (score >= 60) return 'bg-orange-100 text-orange-800 border border-orange-200';
    return 'bg-red-100 text-red-800 border border-red-200';
}

function getSafetyBarColor(score) {
    if (score >= 90) return 'bg-green-500';
    if (score >= 80) return 'bg-lime-500';
    if (score >= 70) return 'bg-yellow-500';
    if (score >= 60) return 'bg-orange-500';
    return 'bg-red-500';
}

function getRouteIcon(type) {
    switch (type) {
        case 'safest': return '🛡️';
        case 'fastest': return '⚡';
        case 'balanced': return '⚖️';
        default: return '🗺️';
    }
}

function getRouteColor(type) {
    switch (type) {
        case 'safest': return '#10b981';
        case 'balanced': return '#f59e0b';
        case 'fastest': return '#ef4444';
        default: return '#6b7280';
    }
}

function showError(message) {
    document.getElementById('loadingState').classList.add('hidden');
    document.getElementById('progressContainer').classList.add('hidden');
    
    // Enhanced error message
    let enhancedMessage = message;
    if (message.includes('No routes found')) {
        enhancedMessage = `${message}\n\nThis could be due to:\n• Invalid addresses\n• Google Maps API limitations\n• Network connectivity issues\n• Backend configuration problems`;
    }
    
    document.getElementById('errorMessage').textContent = enhancedMessage;
    document.getElementById('errorState').classList.remove('hidden');
}

// Initialize when Google Maps API loads
function initializeGoogleMapsCallback() {
    // This function is called by the Google Maps callback
    initializeRoutePlanner();
}

// Event listeners setup
document.addEventListener('DOMContentLoaded', () => {
    // Set up event listeners for buttons
    const recenterBtn = document.getElementById('recenterBtn');
    if (recenterBtn) {
        recenterBtn.addEventListener('click', recenterMap);
    }
    
    const toggleTrafficBtn = document.getElementById('toggleTrafficBtn');
    if (toggleTrafficBtn) {
        toggleTrafficBtn.addEventListener('click', toggleTraffic);
    }
    
    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            window.close();
        } else if (e.key >= '1' && e.key <= '9') {
            const index = parseInt(e.key) - 1;
            if (index < routeData.length) {
                selectRoute(index);
            }
        }
    });
}); 