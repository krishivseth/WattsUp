import { useState } from "react";
import { type JSX } from "react";

interface RouteInputProps {
  originAddress: string;
  onRouteRequest: (destination: string) => void;
  isLoading?: boolean;
}

export const RouteInput = ({ 
  originAddress, 
  onRouteRequest, 
  isLoading = false 
}: RouteInputProps): JSX.Element => {
  const [destination, setDestination] = useState<string>("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (destination.trim()) {
      onRouteRequest(destination.trim());
    }
  };

  const handleOpenMapPlanner = () => {
    if (!originAddress || !destination.trim()) return;
    
    // Open route planner in new tab with parameters
    const params = new URLSearchParams({
      origin: originAddress,
      destination: destination.trim()
    });
    
    // Use 127.0.0.1 instead of localhost to avoid IPv6 resolution issues
    const url = `http://127.0.0.1:8000/route-planner.html?${params.toString()}`;
    window.open(url, '_blank', 'width=1400,height=900');
  };

  return (
    <div className="border-t border-gray-200 pt-3 mt-3">
      <div className="text-lg font-semibold text-gray-800 mb-2">🗺️ Safe Route Planning</div>
      
      <form onSubmit={handleSubmit} className="space-y-3">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">
            From (Apartment)
          </label>
          <div className="bg-gray-50 rounded-lg px-3 py-2 text-xs text-gray-700 border">
            📍 {originAddress || "Address will be detected..."}
          </div>
        </div>
        
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">
            To (Destination)
          </label>
          <input
            type="text"
            value={destination}
            onChange={(e) => setDestination(e.target.value)}
            placeholder="Enter work, school, or destination address..."
            className="w-full px-3 py-2 text-xs border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            disabled={isLoading}
          />
        </div>
        
        <div className="flex gap-2">
          <button
            type="submit"
            disabled={!destination.trim() || !originAddress || isLoading}
            className="flex-1 py-2 px-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white font-medium rounded-lg text-xs transition-colors duration-150"
          >
            {isLoading ? "Analyzing..." : "Get Safe Routes"}
          </button>
          
          <button
            type="button"
            onClick={handleOpenMapPlanner}
            disabled={!destination.trim() || !originAddress}
            className="px-3 py-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white font-medium rounded-lg text-xs transition-colors duration-150"
            title="Open detailed map view"
          >
            🗺️
          </button>
        </div>
      </form>
      
      {originAddress && destination && (
        <div className="mt-2 text-xs text-gray-500">
          💡 Routes will be analyzed for safety based on neighborhood crime data
        </div>
      )}
    </div>
  );
}; 