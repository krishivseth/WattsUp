'use client';

import { useState, useEffect, useRef, useCallback, memo } from 'react';
import { useMap } from 'react-leaflet';
import L from 'leaflet';
import axios from 'axios';
import { MapPin, Navigation, Clock, Route, History, Trash2, X, ArrowRight, Locate, ArrowUpDown, Mic } from 'lucide-react';
import { Marker, Popup } from 'react-leaflet';
import { RouteAIService } from '@/lib/ai-service';

interface Location {
  display_name: string;
  lat: string;
  lon: string;
}

interface CrimeData {
  latitude: string;
  longitude: string;
  ofns_desc: string;
}

interface RouteInfo {
  duration: number;
  distance: number;
}

type TransportMode = 'walking' | 'cycling' | 'driving';

interface ScoredRoute {
  coords: [number, number][];
  duration: number;
  distance: number;
  score: number;
}

interface SavedRoute {
  startLocation: string;
  endLocation: string;
  transportMode: TransportMode;
  routeType: 'fastest' | 'safest';
  timestamp: number;
}

interface RouteSearchProps {
  onRouteUpdate?: (routeData: any) => void;
}

// Custom marker icons
const startIcon = L.divIcon({
  className: 'custom-div-icon',
  html: `
    <div style="
      background: linear-gradient(135deg, #22c55e, #16a34a);
      width: 20px;
      height: 20px;
      border-radius: 50%;
      border: 3px solid white;
      box-shadow: 0 4px 12px rgba(34, 197, 94, 0.4);
      display: flex;
      align-items: center;
      justify-content: center;
    ">
      <div style="
        width: 8px;
        height: 8px;
        background-color: white;
        border-radius: 50%;
      "></div>
    </div>
  `,
  iconSize: [20, 20],
  iconAnchor: [10, 10]
});

const endIcon = L.divIcon({
  className: 'custom-div-icon',
  html: `
    <div style="
      background: linear-gradient(135deg, #ef4444, #dc2626);
      width: 20px;
      height: 20px;
      border-radius: 50%;
      border: 3px solid white;
      box-shadow: 0 4px 12px rgba(239, 68, 68, 0.4);
      display: flex;
      align-items: center;
      justify-content: center;
    ">
      <div style="
        width: 8px;
        height: 8px;
        background-color: white;
        border-radius: 50%;
      "></div>
    </div>
  `,
  iconSize: [20, 20],
  iconAnchor: [10, 10]
});

// Add TypeScript interfaces for SpeechRecognition
interface SpeechRecognitionEvent extends Event {
  results: SpeechRecognitionResultList;
  resultIndex: number;
  interpretation: string;
}

interface SpeechRecognitionErrorEvent extends Event {
  error: string;
  message: string;
}

interface SpeechRecognitionResultList {
  length: number;
  item(index: number): SpeechRecognitionResult;
  [index: number]: SpeechRecognitionResult;
}

interface SpeechRecognitionResult {
  length: number;
  item(index: number): SpeechRecognitionAlternative;
  [index: number]: SpeechRecognitionAlternative;
  isFinal: boolean;
}

interface SpeechRecognitionAlternative {
  transcript: string;
  confidence: number;
}

interface SpeechRecognition extends EventTarget {
  continuous: boolean;
  grammars: any;
  interimResults: boolean;
  lang: string;
  maxAlternatives: number;
  onaudioend: ((this: SpeechRecognition, ev: Event) => any) | null;
  onaudiostart: ((this: SpeechRecognition, ev: Event) => any) | null;
  onend: ((this: SpeechRecognition, ev: Event) => any) | null;
  onerror: ((this: SpeechRecognition, ev: SpeechRecognitionErrorEvent) => any) | null;
  onnomatch: ((this: SpeechRecognition, ev: SpeechRecognitionEvent) => any) | null;
  onresult: ((this: SpeechRecognition, ev: SpeechRecognitionEvent) => any) | null;
  onsoundend: ((this: SpeechRecognition, ev: Event) => any) | null;
  onsoundstart: ((this: SpeechRecognition, ev: Event) => any) | null;
  onspeechend: ((this: SpeechRecognition, ev: Event) => any) | null;
  onspeechstart: ((this: SpeechRecognition, ev: Event) => any) | null;
  onstart: ((this: SpeechRecognition, ev: Event) => any) | null;
  start(): void;
  stop(): void;
  abort(): void;
}

// Define SpeechRecognition constructor type
interface SpeechRecognitionConstructor {
  new(): SpeechRecognition;
  prototype: SpeechRecognition;
}

declare global {
  interface Window {
    SpeechRecognition: SpeechRecognitionConstructor;
    webkitSpeechRecognition: SpeechRecognitionConstructor;
  }
}

const RouteSearch: React.FC<RouteSearchProps> = memo(({ onRouteUpdate }) => {
  const map = useMap();
  const [startLocation, setStartLocation] = useState('');
  const [endLocation, setEndLocation] = useState('');
  const [startSuggestions, setStartSuggestions] = useState<Location[]>([]);
  const [endSuggestions, setEndSuggestions] = useState<Location[]>([]);
  const [routeType, setRouteType] = useState<'fastest' | 'safest'>('fastest');
  const [transportMode, setTransportMode] = useState<TransportMode>('walking');
  const [isCalculating, setIsCalculating] = useState(false);
  const [crimeData, setCrimeData] = useState<CrimeData[]>([]);
  const [routeInfo, setRouteInfo] = useState<RouteInfo | null>(null);
  const [savedRoutes, setSavedRoutes] = useState<SavedRoute[]>([]);
  const [showSavedRoutes, setShowSavedRoutes] = useState(false);
  const [routes, setRoutes] = useState<any[]>([]);
  const [selectedRouteIndex, setSelectedRouteIndex] = useState<number>(0);
  const [isMinimized, setIsMinimized] = useState(false);
  const [isGettingLocation, setIsGettingLocation] = useState(false);
  const currentRouteRef = useRef<L.Polyline | null>(null);
  const startMarkerRef = useRef<L.Marker | null>(null);
  const endMarkerRef = useRef<L.Marker | null>(null);
  const [startPoint, setStartPoint] = useState<[number, number] | null>(null);
  const [endPoint, setEndPoint] = useState<[number, number] | null>(null);
  const [isListening, setIsListening] = useState(false);
  const [isProcessingSpeech, setIsProcessingSpeech] = useState(false);
  const speechRecognition = useRef<SpeechRecognition | null>(null);

  // Load saved routes from localStorage on component mount
  useEffect(() => {
    const saved = localStorage.getItem('savedRoutes');
    if (saved) {
      setSavedRoutes(JSON.parse(saved));
    }
  }, []);

  // Handle URL parameters for automatic route population
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const origin = urlParams.get('origin');
    const destination = urlParams.get('destination');
    
    console.log('safe-route URL Parameters:', { origin, destination });
    
    if (origin && destination) {
      console.log('Auto-populating route from URL parameters');
      setStartLocation(decodeURIComponent(origin));
      setEndLocation(decodeURIComponent(destination));
      
      // Automatically start route calculation after a short delay to ensure state is set
      setTimeout(() => {
        console.log('Auto-starting route calculation...');
        calculateRoute();
      }, 1000);
    }
  }, []); // Run only once on component mount

  // Save route to localStorage
  const saveRoute = () => {
    if (!startLocation || !endLocation) return;

    const newRoute: SavedRoute = {
      startLocation,
      endLocation,
      transportMode,
      routeType,
      timestamp: Date.now()
    };

    // Check for duplicates (same start, end, transport mode, and route type)
    const isDuplicate = savedRoutes.some(route => 
      route.startLocation === newRoute.startLocation &&
      route.endLocation === newRoute.endLocation &&
      route.transportMode === newRoute.transportMode &&
      route.routeType === newRoute.routeType
    );

    if (!isDuplicate) {
      const updatedRoutes = [newRoute, ...savedRoutes].slice(0, 10);
      setSavedRoutes(updatedRoutes);
      localStorage.setItem('savedRoutes', JSON.stringify(updatedRoutes));
    }
  };

  // Load a saved route
  const loadRoute = (route: SavedRoute) => {
    setStartLocation(route.startLocation);
    setEndLocation(route.endLocation);
    setTransportMode(route.transportMode);
    setRouteType(route.routeType);
    setShowSavedRoutes(false);
  };

  // Delete a saved route
  const deleteRoute = (timestamp: number) => {
    const updatedRoutes = savedRoutes.filter(route => route.timestamp !== timestamp);
    setSavedRoutes(updatedRoutes);
    localStorage.setItem('savedRoutes', JSON.stringify(updatedRoutes));
  };

  // Clear route and markers when route type changes
  useEffect(() => {
    clearCurrentRoute();
  }, [routeType]);

  // Function to clear current route and markers
  const clearCurrentRoute = () => {
    console.log('ClearCurrentRoute called');
    
    // IMPROVED route clearing - collect polylines first, then remove them
    const polylinesToRemove: L.Polyline[] = [];
    map.eachLayer((layer: any) => {
      if (layer instanceof L.Polyline && !(layer instanceof L.Polygon)) {
        polylinesToRemove.push(layer);
      }
    });
    
    // Remove all collected polylines
    polylinesToRemove.forEach(polyline => {
      console.log('Removing polyline layer during clear');
      map.removeLayer(polyline);
    });

    // Clear route reference
    if (currentRouteRef.current) {
      map.removeLayer(currentRouteRef.current);
      currentRouteRef.current = null;
    }
    
    // Clear markers
    if (startMarkerRef.current) {
      map.removeLayer(startMarkerRef.current);
      startMarkerRef.current = null;
    }
    if (endMarkerRef.current) {
      map.removeLayer(endMarkerRef.current);
      endMarkerRef.current = null;
    }
    
    // Clear routes array and selection
    setRoutes([]);
    setSelectedRouteIndex(0);
    console.log('Route clearing completed');
  };

  // Fetch crime data
  useEffect(() => {
    const fetchCrimeData = async () => {
      try {
        const response = await axios.get(
          'https://data.cityofnewyork.us/resource/qgea-i56i.json',
          {}
        );
        setCrimeData(response.data);
      } catch (error) {
        console.error('Error fetching crime data:', error);
      }
    };
    fetchCrimeData();
  }, []);

  // Debounce function for search
  const debounce = (func: Function, wait: number) => {
    let timeout: NodeJS.Timeout;
    return (...args: any[]) => {
      clearTimeout(timeout);
      timeout = setTimeout(() => func(...args), wait);
    };
  };

  // Search locations using OpenStreetMap Nominatim API
  const searchLocations = async (query: string) => {
    if (!query) return [];
    try {
      const response = await axios.get(
        `https://nominatim.openstreetmap.org/search`,
        {
          params: {
            q: query,
            format: 'json',
            limit: 5,
            addressdetails: 1,
            countrycodes: 'us', // Focus on US locations
            viewbox: '-74.5,40.4,-73.5,41.0', // NYC bounding box
            bounded: 1
          },
          headers: {
            'User-Agent': 'safe-route/1.0 (https://safe-route.app)', // Required by Nominatim
            'Accept-Language': 'en'
          },
          timeout: 8000 // 8 second timeout
        }
      );
      return response.data;
    } catch (error) {
      console.error('Error searching locations:', error);
      return [];
    }
  };

  const debouncedSearch = debounce(async (query: string, setSuggestions: (locations: Location[]) => void) => {
    if (query.length < 2) {
      setSuggestions([]);
      return;
    }
    const results = await searchLocations(query);
    setSuggestions(results);
  }, 300);

  // Handle location selection
  const handleLocationSelect = (location: Location, isStart: boolean) => {
    if (isStart) {
      setStartLocation(location.display_name);
      setStartSuggestions([]);
      map.setView([parseFloat(location.lat), parseFloat(location.lon)], 15);
    } else {
      setEndLocation(location.display_name);
      setEndSuggestions([]);
    }
  };

  // Handle input blur with delay to allow for suggestion clicks
  const handleInputBlur = (isStart: boolean) => {
    setTimeout(() => {
      if (isStart) {
        setStartSuggestions([]);
      } else {
        setEndSuggestions([]);
      }
    }, 500); // Increased delay to 500ms for easier clicking
  };

  // Calculate crime density for a point
  const calculateCrimeDensity = (lat: number, lon: number, radius: number = 0.003) => {
    return crimeData.reduce((sum, crime) => {
      const dLat = parseFloat(crime.latitude) - lat;
      const dLon = parseFloat(crime.longitude) - lon;
      const distance = Math.sqrt(dLat*dLat + dLon*dLon);
      if (distance > radius) return sum;
      const desc = crime.ofns_desc.toLowerCase();
      const weight = desc.includes('assault') || desc.includes('robbery') ? 8
                   : desc.includes('burglary') || desc.includes('theft')  ? 5
                   : 1;
      return sum + weight;
    }, 0);
  };

  // Calculate overall safety score for a route
  const calculateRouteSafetyScore = (coordinates: [number, number][]) => {
    if (!coordinates.length || !crimeData.length) return 85; // Default decent score
    
    let totalCrimeScore = 0;
    let maxCrimeAtPoint = 0;
    const samplePoints = coordinates.filter((_, index) => index % 5 === 0); // Sample every 5th point for performance
    
    samplePoints.forEach(coord => {
      const crimeScore = calculateCrimeDensity(coord[0], coord[1]);
      totalCrimeScore += crimeScore;
      maxCrimeAtPoint = Math.max(maxCrimeAtPoint, crimeScore);
    });
    
    const avgCrimeScore = totalCrimeScore / samplePoints.length;
    
    // Convert to safety score (0-100, higher is safer)
    // Normalize based on typical crime density ranges
    const normalizedAvg = Math.min(avgCrimeScore / 20, 5); // Cap at 5x normal
    const normalizedMax = Math.min(maxCrimeAtPoint / 50, 4); // Cap at 4x normal
    
    const safetyScore = 100 - (normalizedAvg * 10 + normalizedMax * 15);
    return Math.max(0, Math.min(100, safetyScore));
  };

  // Convert safety score to letter grade
  const getSafetyGrade = (score: number): string => {
    if (score >= 90) return 'A';
    if (score >= 80) return 'B';
    if (score >= 70) return 'C';
    if (score >= 60) return 'D';
    return 'F';
  };

  // Identify high-risk areas along the route
  const identifyHighRiskAreas = (coordinates: [number, number][]) => {
    const highRiskAreas: Array<{lat: number, lng: number, risk: string, description: string}> = [];
    
    coordinates.forEach((coord, index) => {
      if (index % 10 === 0) { // Check every 10th point
        const crimeScore = calculateCrimeDensity(coord[0], coord[1]);
        
        if (crimeScore > 15) { // High crime threshold
          const riskLevel = crimeScore > 30 ? 'high' : 'medium';
          const nearbyIncidents = crimeData.filter(crime => {
            const dLat = parseFloat(crime.latitude) - coord[0];
            const dLon = parseFloat(crime.longitude) - coord[1];
            const distance = Math.sqrt(dLat*dLat + dLon*dLon);
            return distance < 0.005; // Within small radius
          });
          
          const commonCrimes = nearbyIncidents
            .map(c => c.ofns_desc)
            .reduce((acc, crime) => {
              acc[crime] = (acc[crime] || 0) + 1;
              return acc;
            }, {} as Record<string, number>);
          
          const topCrime = Object.entries(commonCrimes)
            .sort(([,a], [,b]) => b - a)[0];
          
          highRiskAreas.push({
            lat: coord[0],
            lng: coord[1],
            risk: riskLevel,
            description: topCrime ? `High ${topCrime[0].toLowerCase()} activity (${topCrime[1]} incidents)` : 'High crime activity detected'
          });
        }
      }
    });
    
    return highRiskAreas;
  };

  // Calculate detailed crime statistics for the route
  const calculateCrimeStats = (coordinates: [number, number][]) => {
    if (!crimeData.length) return { total_incidents: 0, high_risk_areas: 0, crime_types: {} };
    
    const routeCrimes = crimeData.filter(crime => {
      return coordinates.some(coord => {
        const dLat = parseFloat(crime.latitude) - coord[0];
        const dLon = parseFloat(crime.longitude) - coord[1];
        const distance = Math.sqrt(dLat*dLat + dLon*dLon);
        return distance < 0.005; // Within route corridor
      });
    });
    
    const crimeTypes = routeCrimes.reduce((acc, crime) => {
      const type = crime.ofns_desc;
      acc[type] = (acc[type] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);
    
    const highRiskAreas = coordinates.filter(coord => 
      calculateCrimeDensity(coord[0], coord[1]) > 15
    ).length;
    
    return {
      total_incidents: routeCrimes.length,
      high_risk_areas: highRiskAreas,
      crime_types: crimeTypes
    };
  };

  // Format duration in minutes and seconds
  const formatDuration = (seconds: number) => {
    const walkingSpeedMph = 2.6;
    const distanceInMiles = seconds / 3600 * walkingSpeedMph;
    const minutes = Math.floor(distanceInMiles * 60 / walkingSpeedMph);
    const remainingSeconds = Math.round((distanceInMiles * 60 / walkingSpeedMph - minutes) * 60);
    return `${minutes} min ${remainingSeconds} sec`;
  };

  // Format distance in miles
  const formatDistance = (meters: number) => {
    const miles = meters * 0.000621371;
    return `${miles.toFixed(1)} mi`;
  };

  // Get routing API endpoint based on transport mode
  const getRoutingEndpoint = (mode: TransportMode) => {
    switch (mode) {
      case 'walking': return 'https://routing.openstreetmap.de/routed-foot/route/v1/foot';
      case 'cycling': return 'https://routing.openstreetmap.de/routed-bike/route/v1/bike';
      case 'driving': return 'https://routing.openstreetmap.de/routed-car/route/v1/driving';
    }
  };

  // HYBRID: Calculate routes using safe-route's native logic + enhanced safety analysis
  const calculateRoute = async () => {
    if (!startLocation || !endLocation || isCalculating) return;
    setIsCalculating(true);
    clearCurrentRoute();
    setRouteInfo(null);

    try {
      // Clear existing routes array
      setRoutes([]);

      // STEP 1: Geocode start and end locations using safe-route's method
      const [startResp, endResp] = await Promise.all([
        axios.get('https://nominatim.openstreetmap.org/search', { 
          params: { 
            q: startLocation, 
            format: 'json', 
            limit: 1,
            addressdetails: 1,
            countrycodes: 'us', // Focus on US locations
            viewbox: '-74.5,40.4,-73.5,41.0', // NYC bounding box
            bounded: 1
          },
          headers: {
            'User-Agent': 'safe-route/1.0 (https://safe-route.app)', // Required by Nominatim
            'Accept-Language': 'en'
          },
          timeout: 10000 // 10 second timeout
        }),
        axios.get('https://nominatim.openstreetmap.org/search', { 
          params: { 
            q: endLocation, 
            format: 'json', 
            limit: 1,
            addressdetails: 1,
            countrycodes: 'us',
            viewbox: '-74.5,40.4,-73.5,41.0',
            bounded: 1
          },
          headers: {
            'User-Agent': 'safe-route/1.0 (https://safe-route.app)',
            'Accept-Language': 'en'
          },
          timeout: 10000
        })
      ]);

      if (!startResp.data.length) {
        throw new Error(`Could not find start location: "${startLocation}". Please try selecting from the dropdown suggestions.`);
      }
      if (!endResp.data.length) {
        throw new Error(`Could not find end location: "${endLocation}". Please try selecting from the dropdown suggestions.`);
      }

      const start = startResp.data[0];
      const end = endResp.data[0];
      const startCoords = `${start.lon},${start.lat}`;
      const endCoords = `${end.lon},${end.lat}`;

      // STEP 2: Get routes using safe-route's native OpenStreetMap routing
      const routingEndpoint = getRoutingEndpoint(transportMode);
      
      // Calculate multiple route variants using different parameters
      const routeVariants = [
        { type: 'fastest', params: 'alternatives=true&continue_straight=true' },
        { type: 'safest', params: 'alternatives=true&continue_straight=false' }
      ];

      const routePromises = routeVariants.map(async (variant) => {
        try {
          const response = await axios.get(
            `${routingEndpoint}/${startCoords};${endCoords}`,
            {
              params: {
                alternatives: variant.type === 'fastest' ? 'false' : 'true',
                steps: 'true',
                geometries: 'geojson',
                overview: 'full'
              }
            }
          );

          return {
            type: variant.type,
            data: response.data
          };
        } catch (error) {
          console.error(`Error getting ${variant.type} route:`, error);
          return null;
        }
      });

      const routeResults = await Promise.all(routePromises);
      const validRoutes = routeResults.filter(r => r !== null);

      if (!validRoutes.length) {
        throw new Error('No routes could be calculated. Falling back to WattsUp backend...');
      }

      // STEP 3: Process routes and add safe-route's crime analysis
      const processedRoutes = await Promise.all(
        validRoutes.map(async (routeResult: any, index: number) => {
          const route = routeResult.data.routes[0];
          const coordinates = route.geometry.coordinates.map((coord: number[]) => [coord[1], coord[0]]); // Flip lon,lat to lat,lon
          
          // Calculate safety score using safe-route's crime density analysis
          const safetyScore = calculateRouteSafetyScore(coordinates);
          const safetyGrade = getSafetyGrade(safetyScore);
          
          // Identify high-risk areas along the route
          const highRiskAreas = identifyHighRiskAreas(coordinates);
          
          return {
            index,
            type: routeResult.type,
            name: routeResult.type === 'safest' ? '🛡️ Safest Route' : '⚡ Fastest Route',
            distance: `${(route.distance / 1609).toFixed(1)} mi`, // Convert meters to miles
            duration: formatDuration(route.duration),
            safetyScore: Math.round(safetyScore),
            safetyGrade,
            coordinates,
            highRiskAreas,
            crimeStats: calculateCrimeStats(coordinates),
            details: {
              distance_meters: route.distance,
              duration_seconds: route.duration,
              legs: route.legs
            }
          };
        })
      );

      // STEP 4: Try to enhance with WattsUp backend data (optional fallback)
      let backendRouteAdded = false;
      try {
        const backendResponse = await axios.post('http://127.0.0.1:62031/api/safe-routes', {
          origin: startLocation,
          destination: endLocation,
          mode: transportMode === 'cycling' ? 'driving' : transportMode
        }, { timeout: 5000 }); // 5 second timeout

        if (backendResponse.data.routes && backendResponse.data.routes.length > 0) {
          // Add the balanced route from WattsUp if available
          const balancedRoute = backendResponse.data.routes.find((r: any) => r.route_type === 'balanced');
          if (balancedRoute) {
            const coords = decodePolyline(balancedRoute.polyline);
            processedRoutes.push({
              index: processedRoutes.length,
              type: 'balanced',
              name: '⚖️ Balanced Route',
              distance: balancedRoute.distance,
              duration: balancedRoute.duration,
              safetyScore: balancedRoute.overall_safety_score,
              safetyGrade: balancedRoute.overall_safety_grade,
              coordinates: coords,
              highRiskAreas: balancedRoute.high_risk_areas,
              crimeStats: balancedRoute.crime_statistics,
              details: balancedRoute.safety_details
            });
            backendRouteAdded = true;
          }
        }
      } catch (backendError) {
        console.log('WattsUp backend not available, using safe-route-only routes');
      }

      setRoutes(processedRoutes);

      // Set markers for start/end points
      if (startMarkerRef.current) {
        map.removeLayer(startMarkerRef.current);
      }
      if (endMarkerRef.current) {
        map.removeLayer(endMarkerRef.current);
      }

      startMarkerRef.current = L.marker([parseFloat(start.lat), parseFloat(start.lon)], { icon: startIcon }).addTo(map);
      endMarkerRef.current = L.marker([parseFloat(end.lat), parseFloat(end.lon)], { icon: endIcon }).addTo(map);

      // Clear all existing polylines but keep the route data
      const allLayers: any[] = [];
      map.eachLayer((layer: any) => {
        allLayers.push(layer);
      });
      
      // Remove polylines but keep markers
      allLayers.forEach(layer => {
        if (layer instanceof L.Polyline && !(layer instanceof L.Polygon)) {
          try {
            map.removeLayer(layer);
          } catch (e) {
            console.error('Error removing layer:', e);
          }
        }
      });

      // Clear current route reference
      if (currentRouteRef.current) {
        try {
          map.removeLayer(currentRouteRef.current);
        } catch (e) {
          console.log('CurrentRouteRef already removed');
        }
        currentRouteRef.current = null;
      }
      
      // Select the safest route by default and display it
      const defaultRoute = processedRoutes.find((r: any) => r.type === 'safest') || processedRoutes[0];
      setSelectedRouteIndex(defaultRoute.index);
      displayRoute(defaultRoute);

      // Save the route after successful calculation
      saveRoute();

      // Automatically minimize the route planner after successful route calculation
      setTimeout(() => {
        setIsMinimized(true);
      }, 1000);

    } catch (err: any) {
      console.error('Route calculation error:', err);
      
      // Show user-friendly error message
      if (err.message.includes('Could not find')) {
        alert(err.message + '\n\nTip: Type a few characters and select from the dropdown suggestions for best results.');
        setIsCalculating(false);
        return;
      }
      
      // Final fallback: try WattsUp backend only
      try {
        console.log('OpenStreetMap routing failed, falling back to WattsUp backend only...');
        const response = await axios.post('http://127.0.0.1:62031/api/safe-routes', {
          origin: startLocation,
          destination: endLocation,
          mode: transportMode === 'cycling' ? 'driving' : transportMode
        });

        if (response.data.routes) {
          const backendRoutes = response.data.routes.map((route: any, index: number) => {
            const coords = decodePolyline(route.polyline);
            return {
              index,
              type: route.route_type,
              name: route.route_type === 'safest' ? '🛡️ Safest Route' : 
                    route.route_type === 'fastest' ? '⚡ Fastest Route' : 
                    '⚖️ Balanced Route',
              distance: route.distance,
              duration: route.duration,
              safetyScore: route.overall_safety_score,
              safetyGrade: route.overall_safety_grade,
              coordinates: coords,
              highRiskAreas: route.high_risk_areas,
              crimeStats: route.crime_statistics,
              details: route.safety_details
            };
          });
          
          setRoutes(backendRoutes);
          const defaultRoute = backendRoutes[0];
          setSelectedRouteIndex(0);
          displayRoute(defaultRoute);
        } else {
          throw new Error('No routes available from any source');
        }
      } catch (finalError) {
        alert('Failed to calculate route. Please check your internet connection and try again.');
      }
    } finally {
      setIsCalculating(false);
    }
  };

  // Add new function to decode Google's polyline format
  const decodePolyline = (encoded: string): [number, number][] => {
    const coordinates: [number, number][] = [];
    let index = 0;
    let lat = 0;
    let lng = 0;

    while (index < encoded.length) {
      let byte = 0;
      let shift = 0;
      let result = 0;

      do {
        byte = encoded.charCodeAt(index++) - 63;
        result |= (byte & 0x1f) << shift;
        shift += 5;
      } while (byte >= 0x20);

      const deltaLat = (result & 1) !== 0 ? ~(result >> 1) : result >> 1;
      lat += deltaLat;

      shift = 0;
      result = 0;

      do {
        byte = encoded.charCodeAt(index++) - 63;
        result |= (byte & 0x1f) << shift;
        shift += 5;
      } while (byte >= 0x20);

      const deltaLng = (result & 1) !== 0 ? ~(result >> 1) : result >> 1;
      lng += deltaLng;

      coordinates.push([lat / 1e5, lng / 1e5]);
    }

    return coordinates;
  };

  // Add new function to display a selected route
  const displayRoute = (route: any) => {
    console.log('DisplayRoute called for:', route.type, 'Route index:', route.index);
    
    // ENHANCED route clearing with multiple passes to ensure all routes are removed
    // First pass: remove all polylines except polygons
    const allLayers: any[] = [];
    map.eachLayer((layer: any) => {
      allLayers.push(layer);
    });
    
    // Remove polylines in a separate loop to avoid iterator issues
    allLayers.forEach(layer => {
      if (layer instanceof L.Polyline && !(layer instanceof L.Polygon)) {
        try {
          map.removeLayer(layer);
          console.log('Removed a polyline layer');
        } catch (e) {
          console.error('Error removing layer:', e);
        }
      }
    });

    // Clear the current route reference if it exists
    if (currentRouteRef.current) {
      console.log('Clearing currentRouteRef');
      try {
        map.removeLayer(currentRouteRef.current);
      } catch (e) {
        console.log('CurrentRouteRef already removed');
      }
      currentRouteRef.current = null;
    }
    
    // Add a small delay to ensure previous operations complete
    setTimeout(() => {
      // Set route info
      const durationInSeconds = parseInt(route.duration.split(' ')[0]) * 60; // Rough conversion
      const distanceInMeters = parseFloat(route.distance.split(' ')[0]) * 1609; // Convert miles to meters
      setRouteInfo({ duration: durationInSeconds, distance: distanceInMeters });

      // Get color based on route type
      const getRouteColor = (type: string) => {
        switch (type) {
          case 'safest': return '#10b981'; // Green
          case 'fastest': return '#3b82f6'; // Blue  
          case 'balanced': return '#f59e0b'; // Orange
          default: return '#6b7280'; // Gray
        }
      };

      console.log('Drawing route with color:', getRouteColor(route.type), 'for type:', route.type);

      // Draw the NEW route and store reference
      const newRoute = L.polyline(route.coordinates, {
        color: getRouteColor(route.type),
        weight: 8, // Make it thicker for better visibility
        opacity: 0.9,
        dashArray: route.type === 'safest' ? '10,5' : undefined,
        lineCap: 'round',
        lineJoin: 'round'
      });
      
      // Add to map and store reference
      newRoute.addTo(map);
      currentRouteRef.current = newRoute;

      console.log('Route drawn successfully, fitting bounds...');

      // Fit map to route bounds
      if (newRoute.getBounds().isValid()) {
        map.fitBounds(newRoute.getBounds(), { padding: [20, 20] });
      }

      // Create route data object for parent component
      const routeData = {
        start: {
          lat: route.coordinates[0][0],
          lng: route.coordinates[0][1],
          address: startLocation
        },
        end: {
          lat: route.coordinates[route.coordinates.length - 1][0],
          lng: route.coordinates[route.coordinates.length - 1][1],
          address: endLocation
        },
        distance: route.distance,
        duration: route.duration,
        path: route.coordinates,
        safetyScore: route.safetyScore,
        safetyGrade: route.safetyGrade,
        routeType: route.type,
        highRiskAreas: route.highRiskAreas,
        crimeStats: route.crimeStats
      };

      // Pass route data to parent component
      if (onRouteUpdate) {
        onRouteUpdate(routeData);
      }

      console.log('Route display completed for:', route.type);
    }, 50); // Small delay to ensure clean state
  };

  // Add function to handle route card selection
  const selectRoute = (routeIndex: number) => {
    console.log('SelectRoute called for index:', routeIndex, 'Current routes:', routes.length);
    setSelectedRouteIndex(routeIndex);
    const selectedRoute = routes[routeIndex];
    if (selectedRoute) {
      console.log('Selected route:', selectedRoute.name, 'Type:', selectedRoute.type);
      displayRoute(selectedRoute);
    } else {
      console.error('No route found at index:', routeIndex);
    }
  };

  const getTransportIcon = (mode: TransportMode) => {
    switch (mode) {
      case 'walking': return '🚶‍♂️';
      case 'cycling': return '🚴‍♂️';
      case 'driving': return '🚗';
    }
  };

  const getRouteTypeColor = (type: 'fastest' | 'safest') => {
    return type === 'fastest' ? 'from-blue-500 to-cyan-500' : 'from-green-500 to-emerald-500';
  };

  const handleRouteUpdate = useCallback((start: [number, number], end: [number, number]) => {
    if (startPoint === start && endPoint === end) return;

    setStartPoint(start);
    setEndPoint(end);

    // Create route data object
    const routeData = {
      start: {
        lat: start[0],
        lng: start[1],
        address: "Starting Point" // You can add geocoding here to get actual addresses
      },
      end: {
        lat: end[0],
        lng: end[1],
        address: "Ending Point"
      },
      distance: "2.0 mi", // Calculate actual distance
      duration: "42 min 16 sec", // Calculate actual duration
      path: [start, end], // Add actual path points
      safetyScore: 75, // Calculate actual safety score
      highRiskAreas: [
        {
          lat: 40.7300,
          lng: -73.9900,
          risk: "medium",
          description: "Area with moderate crime rate"
        }
      ],
      wellLitAreas: [
        {
          lat: 40.7200,
          lng: -73.9950,
          description: "Well-lit commercial area"
        }
      ]
    };

    // Pass route data to parent component
    if (onRouteUpdate) {
      onRouteUpdate(routeData);
    }
  }, [onRouteUpdate, startPoint, endPoint]);

  // Get current location function
  const getCurrentLocation = async (isStart: boolean) => {
    if (!navigator.geolocation) {
      alert('Geolocation is not supported by this browser.');
      return;
    }

    setIsGettingLocation(true);
    
    try {
      const position = await new Promise<GeolocationPosition>((resolve, reject) => {
        navigator.geolocation.getCurrentPosition(resolve, reject, {
          enableHighAccuracy: true,
          timeout: 10000,
          maximumAge: 60000
        });
      });

      const { latitude, longitude } = position.coords;
      
      // Reverse geocode to get address
      try {
        const response = await axios.get(
          `https://nominatim.openstreetmap.org/reverse?format=json&lat=${latitude}&lon=${longitude}&zoom=18&addressdetails=1`
        );
        
        const address = response.data.display_name;
        
        if (isStart) {
          setStartLocation(address);
          setStartPoint([latitude, longitude]);
        } else {
          setEndLocation(address);
          setEndPoint([latitude, longitude]);
        }
        
        // Center map on the new location
        map.setView([latitude, longitude], 15);
        
      } catch (error) {
        // If reverse geocoding fails, use coordinates as fallback
        const fallbackAddress = `${latitude.toFixed(6)}, ${longitude.toFixed(6)}`;
        
        if (isStart) {
          setStartLocation(fallbackAddress);
          setStartPoint([latitude, longitude]);
        } else {
          setEndLocation(fallbackAddress);
          setEndPoint([latitude, longitude]);
        }
        
        map.setView([latitude, longitude], 15);
      }
      
    } catch (error) {
      console.error('Error getting location:', error);
      alert('Unable to get your current location. Please check your browser permissions and try again.');
    } finally {
      setIsGettingLocation(false);
    }
  };

  // Switch locations function
  const switchLocations = () => {
    // Switch location strings
    const tempLocation = startLocation;
    setStartLocation(endLocation);
    setEndLocation(tempLocation);
    
    // Switch coordinates
    const tempPoint = startPoint;
    setStartPoint(endPoint);
    setEndPoint(tempPoint);
    
    // Switch suggestions
    const tempSuggestions = startSuggestions;
    setStartSuggestions(endSuggestions);
    setEndSuggestions(tempSuggestions);
    
    // Clear current route since locations changed
    clearCurrentRoute();
    setRouteInfo(null);
  };

  // Initialize speech recognition
  useEffect(() => {
    if ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window) {
      const SpeechRecognitionAPI = window.SpeechRecognition || window.webkitSpeechRecognition;
      speechRecognition.current = new SpeechRecognitionAPI();
      speechRecognition.current.continuous = false;
      speechRecognition.current.interimResults = false;
      speechRecognition.current.lang = 'en-US';

      speechRecognition.current.onresult = async (event: SpeechRecognitionEvent) => {
        const transcript = event.results[0][0].transcript;
        console.log('Voice input:', transcript);
        setIsListening(false);
        setIsProcessingSpeech(true);
        
        try {
          const locations = await RouteAIService.processVoiceInput(transcript);
          if (locations) {
            // Handle current location for start point
            if (locations.startLocation === "USE_CURRENT_LOCATION") {
              await getCurrentLocation(true); // Get current location for start point
            } else {
              setStartLocation(locations.startLocation);
            }
            
            // Handle current location for end point
            if (locations.endLocation === "USE_CURRENT_LOCATION") {
              await getCurrentLocation(false); // Get current location for end point
            } else {
              setEndLocation(locations.endLocation);
            }
            
            // Set transport mode if specified
            if (locations.transportMode) {
              setTransportMode(locations.transportMode);
            }
            
            // Set route type if specified
            if (locations.routeType) {
              setRouteType(locations.routeType);
            }
            
            // Clear any existing suggestions
            setStartSuggestions([]);
            setEndSuggestions([]);
            
            // Wait for state updates to complete, then automatically calculate route
            setTimeout(() => {
              calculateRoute();
            }, 300);
          } else {
            alert('Could not understand the locations. Please try again.');
          }
        } catch (error) {
          console.error('Error processing speech:', error);
          alert('Error processing speech. Please try again.');
        } finally {
          setIsProcessingSpeech(false);
        }
      };

      speechRecognition.current.onerror = (event: SpeechRecognitionErrorEvent) => {
        console.error('Speech recognition error', event.error);
        setIsListening(false);
        setIsProcessingSpeech(false);
        alert('Error with speech recognition. Please try again or use text input.');
      };
    }
  }, []);

  const startVoiceInput = () => {
    if (speechRecognition.current) {
      setIsListening(true);
      speechRecognition.current.start();
    } else {
      alert('Speech recognition is not supported in your browser.');
    }
  };

  return (
    <div className="absolute left-4 top-20 bottom-6 z-[1000] w-80 flex flex-col">
      {/* Main Search Panel */}
      <div className="bg-white rounded-2xl shadow-2xl border border-gray-200 flex flex-col max-h-full">
        {/* Header */}
        <div className="p-4 border-b border-gray-100">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center space-x-3">
              <div className="w-8 h-8 bg-gradient-to-r from-green-500 to-emerald-600 rounded-lg flex items-center justify-center">
                <Navigation className="w-4 h-4 text-white" />
              </div>
              <div>
                <h2 className="text-base font-bold text-gray-800">Route Planner</h2>
                <p className="text-xs text-gray-500">Find your safe path</p>
              </div>
            </div>
            <button
              onClick={() => setIsMinimized(!isMinimized)}
              className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors"
            >
              {isMinimized ? (
                <ArrowRight className="w-4 h-4 text-gray-600 rotate-90" />
              ) : (
                <ArrowRight className="w-4 h-4 text-gray-600 -rotate-90" />
              )}
            </button>
          </div>

          {/* Quick Options */}
          <div className="flex space-x-2">
            <select
              value={transportMode}
              onChange={(e) => setTransportMode(e.target.value as TransportMode)}
              className="flex-1 p-2 text-xs border border-gray-200 rounded-lg bg-white focus:ring-2 focus:ring-green-500 focus:border-green-500"
            >
              <option value="walking">🚶‍♂️ Walking</option>
              <option value="cycling">🚴‍♂️ Cycling</option>
              <option value="driving">🚗 Driving</option>
            </select>
            <select
              value={routeType}
              onChange={(e) => setRouteType(e.target.value as 'fastest' | 'safest')}
              className="flex-1 p-2 text-xs border border-gray-200 rounded-lg bg-white focus:ring-2 focus:ring-green-500 focus:border-green-500"
            >
              <option value="fastest">⚡ Fastest</option>
              <option value="safest">🛡️ Safest</option>
            </select>
          </div>
        </div>

        {/* Content Area */}
        <div className={`flex-1 overflow-y-auto ${isMinimized ? 'hidden' : ''}`}>
          <div className="p-4 space-y-4">
            {/* Location Inputs */}
            <div className="space-y-3">
              {/* From Input */}
              <div className="relative">
                <label className="block text-xs font-medium text-gray-700 mb-1">From</label>
                <div className="relative">
                  <div className="absolute left-3 top-1/2 transform -translate-y-1/2 w-2.5 h-2.5 bg-green-500 rounded-full"></div>
                  <input
                    type="text"
                    value={startLocation}
                    onChange={(e) => {
                      setStartLocation(e.target.value);
                      debouncedSearch(e.target.value, setStartSuggestions);
                    }}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && startSuggestions.length > 0) {
                        handleLocationSelect(startSuggestions[0], true);
                      }
                    }}
                    onBlur={() => handleInputBlur(true)}
                    placeholder="Enter starting location"
                    className="w-full pl-8 pr-10 py-2.5 text-sm border border-gray-200 rounded-lg text-gray-700 placeholder-gray-400 focus:ring-2 focus:ring-green-500 focus:border-green-500"
                  />
                  <button
                    onClick={() => getCurrentLocation(true)}
                    disabled={isGettingLocation}
                    className="absolute right-2 top-1/2 transform -translate-y-1/2 p-1 hover:bg-green-50 rounded-md transition-colors"
                    title="Use current location"
                  >
                    {isGettingLocation ? (
                      <div className="w-3.5 h-3.5 border-2 border-green-300 border-t-green-600 rounded-full animate-spin"></div>
                    ) : (
                      <Locate className="w-3.5 h-3.5 text-green-600" />
                    )}
                  </button>
                </div>
                {startSuggestions.length > 0 && (
                  <div className="absolute z-[9999] w-full mt-1 bg-white rounded-lg shadow-2xl border-2 border-green-200 max-h-40 overflow-y-auto">
                    {startSuggestions.map((location, index) => (
                      <div
                        key={index}
                        className="p-3 hover:bg-green-50 active:bg-green-100 cursor-pointer text-gray-700 border-b border-gray-100 last:border-b-0 flex items-center gap-3 text-sm transition-colors"
                        onClick={() => handleLocationSelect(location, true)}
                        onMouseDown={(e) => e.preventDefault()}
                      >
                        <MapPin className="w-4 h-4 text-green-500 flex-shrink-0" />
                        <span className="truncate font-medium">{location.display_name}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Switch Button */}
              <div className="flex justify-center">
                <button
                  onClick={switchLocations}
                  disabled={!startLocation || !endLocation}
                  className="p-1.5 bg-gray-100 hover:bg-gray-200 rounded-full transition-colors disabled:opacity-50"
                  title="Switch locations"
                >
                  <ArrowUpDown className="w-3.5 h-3.5 text-gray-600" />
                </button>
              </div>

              {/* To Input */}
              <div className="relative">
                <label className="block text-xs font-medium text-gray-700 mb-1">To</label>
                <div className="relative">
                  <div className="absolute left-3 top-1/2 transform -translate-y-1/2 w-2.5 h-2.5 bg-red-500 rounded-full"></div>
                  <input
                    type="text"
                    value={endLocation}
                    onChange={(e) => {
                      setEndLocation(e.target.value);
                      debouncedSearch(e.target.value, setEndSuggestions);
                    }}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && endSuggestions.length > 0) {
                        handleLocationSelect(endSuggestions[0], false);
                      }
                    }}
                    onBlur={() => handleInputBlur(false)}
                    placeholder="Enter destination"
                    className="w-full pl-8 pr-10 py-2.5 text-sm border border-gray-200 rounded-lg text-gray-700 placeholder-gray-400 focus:ring-2 focus:ring-green-500 focus:border-green-500"
                  />
                  <button
                    onClick={() => getCurrentLocation(false)}
                    disabled={isGettingLocation}
                    className="absolute right-2 top-1/2 transform -translate-y-1/2 p-1 hover:bg-green-50 rounded-md transition-colors"
                    title="Use current location"
                  >
                    {isGettingLocation ? (
                      <div className="w-3.5 h-3.5 border-2 border-green-300 border-t-green-600 rounded-full animate-spin"></div>
                    ) : (
                      <Locate className="w-3.5 h-3.5 text-green-600" />
                    )}
                  </button>
                </div>
                {endSuggestions.length > 0 && (
                  <div className="absolute z-[9999] w-full mt-1 bg-white rounded-lg shadow-2xl border-2 border-green-200 max-h-40 overflow-y-auto">
                    {endSuggestions.map((location, index) => (
                      <div
                        key={index}
                        className="p-3 hover:bg-green-50 active:bg-green-100 cursor-pointer text-gray-700 border-b border-gray-100 last:border-b-0 flex items-center gap-3 text-sm transition-colors"
                        onClick={() => handleLocationSelect(location, false)}
                        onMouseDown={(e) => e.preventDefault()}
                      >
                        <MapPin className="w-4 h-4 text-green-500 flex-shrink-0" />
                        <span className="truncate font-medium">{location.display_name}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Calculate Route Button */}
            <button
              onClick={calculateRoute}
              disabled={!startLocation || !endLocation || isCalculating}
              className="w-full py-3 px-4 bg-gradient-to-r from-green-600 to-emerald-600 text-white rounded-lg font-semibold hover:from-green-700 hover:to-emerald-700 disabled:from-gray-300 disabled:to-gray-400 disabled:cursor-not-allowed transition-all duration-200 shadow-lg hover:shadow-xl flex items-center justify-center gap-2 text-sm"
            >
              {isCalculating ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                  <span>Finding Routes...</span>
                </>
              ) : (
                <>
                  <Navigation className="w-4 h-4" />
                  <span>Find Safe Routes</span>
                </>
              )}
            </button>

            {/* Route Options */}
            {routes.length > 0 && (
              <div className="space-y-2">
                <h3 className="text-xs font-semibold text-gray-700 flex items-center gap-2">
                  <Route className="w-3.5 h-3.5" />
                  Available Routes
                </h3>
                <div className="space-y-1.5">
                  {routes.map((route: any, index: number) => (
                    <div
                      key={index}
                      onClick={() => selectRoute(index)}
                      className={`p-3 rounded-lg border cursor-pointer transition-all duration-200 ${
                        selectedRouteIndex === index
                          ? 'border-green-500 bg-green-50 shadow-sm' 
                          : 'border-gray-200 bg-white hover:border-gray-300 hover:bg-gray-50'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1.5">
                        <div className="flex items-center gap-1.5">
                          <span className="text-sm">{route.name.split(' ')[0]}</span>
                          <span className="font-medium text-gray-800 text-sm">{route.name.substring(2)}</span>
                        </div>
                        <div className={`w-2.5 h-2.5 rounded-full border ${
                          selectedRouteIndex === index 
                            ? 'bg-green-500 border-green-500' 
                            : 'border-gray-300'
                        }`}></div>
                      </div>
                      <div className="flex items-center gap-3 text-xs text-gray-600 mb-1.5">
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {route.duration}
                        </span>
                        <span className="flex items-center gap-1">
                          <Route className="w-3 h-3" />
                          {route.distance}
                        </span>
                      </div>
                      <div className={`px-2 py-0.5 rounded text-xs font-medium text-center ${
                        route.safetyGrade === 'A' ? 'bg-green-100 text-green-800' :
                        route.safetyGrade === 'B' ? 'bg-blue-100 text-blue-800' :
                        route.safetyGrade === 'C' ? 'bg-yellow-100 text-yellow-800' :
                        route.safetyGrade === 'D' ? 'bg-orange-100 text-orange-800' :
                        'bg-red-100 text-red-800'
                      }`}>
                        Safety: {route.safetyGrade} ({route.safetyScore}/100)
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Current Route Info */}
            {routeInfo && (
              <div className="bg-gradient-to-r from-green-600 to-emerald-600 p-4 rounded-xl text-white">
                <div className="flex items-center gap-3 mb-2">
                  <span className="text-2xl">{getTransportIcon(transportMode)}</span>
                  <div>
                    <p className="text-green-100 text-sm font-medium">
                      {routeType === 'fastest' ? 'Fastest Route' : 'Safest Route'}
                    </p>
                    <div className="flex items-center gap-4 mt-1">
                      <div className="flex items-center gap-1">
                        <Clock className="w-4 h-4" />
                        <span className="font-semibold">{formatDuration(routeInfo.duration)}</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <Route className="w-4 h-4" />
                        <span className="font-semibold">{formatDistance(routeInfo.distance)}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        {!isMinimized && (
          <div className="p-4 border-t border-gray-100 bg-gray-50 rounded-b-2xl">
            <div className="flex items-center justify-between text-sm text-gray-600">
              <span className="flex items-center gap-2">
                <div className="w-2 h-2 bg-green-400 rounded-full"></div>
                Live safety data
              </span>
              <button
                onClick={() => setShowSavedRoutes(!showSavedRoutes)}
                className="flex items-center gap-2 hover:text-green-600 transition-colors"
              >
                <History className="w-4 h-4" />
                History
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Saved Routes Panel */}
      {showSavedRoutes && savedRoutes.length > 0 && (
        <div className="mt-4 bg-white rounded-2xl shadow-2xl border border-gray-200 max-h-64 flex flex-col">
          <div className="p-4 border-b border-gray-100 flex items-center justify-between">
            <h3 className="font-semibold text-gray-800 flex items-center gap-2">
              <History className="w-4 h-4" />
              Recent Routes
            </h3>
            <button
              onClick={() => setShowSavedRoutes(false)}
              className="p-1 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <X className="w-4 h-4 text-gray-500" />
            </button>
          </div>
          <div className="overflow-y-auto flex-1">
            {savedRoutes.map((route) => (
              <div
                key={route.timestamp}
                className="p-4 border-b border-gray-50 last:border-b-0 hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div 
                    className="flex-1 cursor-pointer"
                    onClick={() => loadRoute(route)}
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-lg">{getTransportIcon(route.transportMode)}</span>
                      <span className="px-2 py-1 rounded-full text-xs font-medium text-white bg-gradient-to-r from-green-600 to-emerald-600">
                        {route.routeType}
                      </span>
                    </div>
                    <div className="space-y-1 text-sm">
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                        <span className="text-gray-800 truncate">{route.startLocation.split(',')[0]}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 bg-red-500 rounded-full"></div>
                        <span className="text-gray-800 truncate">{route.endLocation.split(',')[0]}</span>
                      </div>
                    </div>
                    <div className="text-xs text-gray-500 mt-2">
                      {new Date(route.timestamp).toLocaleDateString()}
                    </div>
                  </div>
                  <button
                    onClick={() => deleteRoute(route.timestamp)}
                    className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Markers */}
      {startPoint && (
        <Marker position={startPoint} icon={startIcon}>
          <Popup>Starting Point</Popup>
        </Marker>
      )}
      {endPoint && (
        <Marker position={endPoint} icon={endIcon}>
          <Popup>Destination</Popup>
        </Marker>
      )}
    </div>
  );
});

RouteSearch.displayName = 'RouteSearch';

export default RouteSearch; 