import { useState, useEffect } from "react";
import logo from "./assets/WattsUpLogo.png";
import { Tag } from "./components/Tag";
import { SafetyRating } from "./components/SafetyRating";
import { SafetyDetails } from "./components/SafetyDetails";
import { ReviewsDetails } from "./components/ReviewsDetails";
import { RouteInput } from "./components/RouteInput";
import type { SafetyAnalysis } from "./types/safety";
import type { ReviewsAnalysis } from "./types/reviews";

interface EnergyCostData {
  annual_summary: {
    average_monthly_bill: number;
    total_kwh: number;
    total_bill: number;
  }
}

function App() {
  const [address, setAddress] = useState<string>("");
  const [numRooms, setNumRooms] = useState<number>(1);
  const [cost, setCost] = useState<number | null>(30);
  const [error, setError] = useState<string>("");
  const [safetyData, setSafetyData] = useState<SafetyAnalysis | null>(null);
  const [safetyLoading, setSafetyLoading] = useState<boolean>(false);
  const [safetyError, setSafetyError] = useState<string>("");
  const [showSafetyDetails, setShowSafetyDetails] = useState<boolean>(false);
  const [reviewsData, setReviewsData] = useState<ReviewsAnalysis | null>(null);
  const [reviewsLoading, setReviewsLoading] = useState<boolean>(false);
  const [reviewsError, setReviewsError] = useState<string>("");
  const [showReviewsDetails, setShowReviewsDetails] = useState<boolean>(false);
  const [routeLoading, setRouteLoading] = useState<boolean>(false);

  const extractAddressAndRooms = async (): Promise<{address: string, numRooms: number}> => {
    try {
      const [tab] = await chrome.tabs.query({
        active: true,
        currentWindow: true,
      });

      if (!tab.url?.includes("streeteasy.com")) {
        throw new Error("WattsUp is only supported on StreetEasy listings");
      }

      const response = await chrome.tabs.sendMessage(tab.id!, {
        action: "extractAddress",
      });

      if (!response || !response.address) {
        throw new Error("Could not find address on this page");
      }

      return {
        address: response.address,
        numRooms: response.numRooms || 1 // Fallback to 1 if numRooms not found
      };
    } catch (err) {
      throw new Error(
        `Failed to extract listing info: ${
          err instanceof Error ? err.message : "Unknown error"
        }`
      );
    }
  };

  const getEnergyCost = async (address: string, numRooms: number): Promise<number> => {
    const API_ENDPOINT = "http://127.0.0.1:62031/api/estimate";

    try {
      const response = await fetch(API_ENDPOINT, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ address, num_rooms: numRooms }),
      });

      if (!response.ok) {
        throw new Error(`API request failed: ${response.status}`);
      }

      const data: EnergyCostData = await response.json();
      return data.annual_summary.average_monthly_bill || 0;
    } catch {
      return 0;
    }
  };

  const getSafetyAnalysis = async (address: string): Promise<SafetyAnalysis | null> => {
    const API_ENDPOINT = "http://127.0.0.1:62031/api/safety";

    try {
      setSafetyLoading(true);
      setSafetyError("");

      // Extract zip code and borough from address for better analysis
      const response = await fetch(API_ENDPOINT, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ address }),
      });

      if (!response.ok) {
        throw new Error(`Safety API request failed: ${response.status}`);
      }

      const data: SafetyAnalysis = await response.json();
      return data;
    } catch (err) {
      setSafetyError(err instanceof Error ? err.message : "Failed to get safety data");
      return null;
    } finally {
      setSafetyLoading(false);
    }
  };

  const getReviewsAnalysis = async (address: string): Promise<ReviewsAnalysis | null> => {
    const API_ENDPOINT = "http://127.0.0.1:62031/api/reviews";

    try {
      setReviewsLoading(true);
      setReviewsError("");

      const response = await fetch(API_ENDPOINT, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ address }),
      });

      if (!response.ok) {
        throw new Error(`Reviews API request failed: ${response.status}`);
      }

      const data: ReviewsAnalysis = await response.json();
      
      // Check if no reviews were found
      if (data.status === 'no_reviews') {
        setReviewsError(data.message || "No reviews found for this building");
        return null;
      }
      
      return data;
    } catch (err) {
      setReviewsError(err instanceof Error ? err.message : "Failed to get reviews data");
      return null;
    } finally {
      setReviewsLoading(false);
    }
  };

  const handleRouteRequest = async (destination: string) => {
    try {
      setRouteLoading(true);
      
      // For now, we'll just open the route planner
      // The actual route analysis will happen in the route planner page
      const params = new URLSearchParams({
        origin: address,
        destination: destination
      });
      
      // Use safe-route interface with fixed route switching  
      const url = `http://127.0.0.1:3005/route?${params.toString()}`;
      window.open(url, '_blank', 'width=1400,height=900');
    } catch (error) {
      console.error('Failed to open route planner:', error);
    } finally {
      setRouteLoading(false);
    }
  };

  useEffect(() => {
    extractAddressAndRooms()
      .then(({ address, numRooms }) => {
        setAddress(address);
        setNumRooms(numRooms);
        getEnergyCost(address, numRooms)
          .then(setCost)
          .catch((err: Error) => setError(err.message));
      })
      .catch((err: Error) =>
        setError(
          err instanceof Error ? err.message : "Failed to extract listing info"
        )
      );
  }, []);

  useEffect(() => {
    if (address) {
      getSafetyAnalysis(address)
        .then(setSafetyData)
        .catch(err => setSafetyError(err.message));
      
      getReviewsAnalysis(address)
        .then(setReviewsData)
        .catch(err => setReviewsError(err.message));
    }
  }, [address]);

  return (
    <div className="w-80 min-h-96 max-h-[600px] overflow-y-auto p-4 bg-white rounded-2xl shadow-lg border border-gray-200">
      <div className="flex flex-col gap-4">
        <div className="flex items-center gap-3 mb-1">
          <img src={logo} alt="What The Rent?!" className="h-10" />
          <div className="text-2xl font-bold h-10 text-center tracking-tight text-gray-800">
            What The Rent?!
          </div>
        </div>
        <div className="border-b border-gray-200 mx-[-16px]" />
        <div className="bg-gray-50 rounded-lg text-xs px-3 py-2 text-gray-700 space-y-1">
          <div className="flex items-center gap-1">
            <span className="text-gray-400">📍</span>
            {address || <span className="italic text-gray-400">Address will be detected automatically...</span>}
          </div>
          {address && (
            <div className="flex items-center gap-1">
              <span className="text-gray-400">🏠</span>
              <span>{numRooms === 0 ? 'Studio' : `${numRooms} bedroom${numRooms > 1 ? 's' : ''}`}</span>
            </div>
          )}
        </div>
        <div className="mt-2">
          <div className="text-lg font-semibold text-gray-800 mb-1">Monthly Energy Estimate</div>
          {cost !== null ? (
            <div className="flex flex-col gap-1">
              <div className="text-3xl font-extrabold text-green-700">${cost}</div>
              <Tag efficiency={cost} />
            </div>
          ) : (
            <div className="text-sm opacity-80 mb-4 text-center animate-pulse text-gray-500">
              Calculating energy costs...
            </div>
          )}
        </div>
        <ul className="ml-2 list-disc list-inside mt-2 space-y-1 text-gray-700 text-sm">
          <li>Predicted monthly energy costs</li>
          <li>Based on building data and usage patterns</li>
          <li>Sustainability rating for this apartment</li>
        </ul>

        {/* Safety Rating Section */}
        <div className="border-t border-gray-200 pt-3 mt-3">
          <div className="text-lg font-semibold text-gray-800 mb-2">Area Safety</div>
          {safetyData ? (
            <div className="space-y-3">
              <SafetyRating
                grade={safetyData.safety_rating.grade}
                score={safetyData.safety_rating.score}
                description={safetyData.safety_rating.description}
                totalComplaints={safetyData.safety_metrics.total_complaints}
                isLoading={safetyLoading}
              />
              <SafetyDetails
                summary={safetyData.llm_summary || safetyData.safety_summary}
                complaintBreakdown={safetyData.complaint_breakdown}
                recommendations={safetyData.llm_recommendations || safetyData.recommendations}
                recentActivity={safetyData.recent_activity}
                isExpanded={showSafetyDetails}
                onToggle={() => setShowSafetyDetails(!showSafetyDetails)}
              />
            </div>
          ) : safetyLoading ? (
            <div className="text-sm opacity-80 mb-4 text-center animate-pulse text-gray-500">
              Analyzing area safety...
            </div>
          ) : safetyError ? (
            <div className="bg-yellow-500/10 border border-yellow-300 text-yellow-700 rounded-lg p-2 text-xs">
              {safetyError}
            </div>
          ) : (
            <div className="text-xs text-gray-500 italic">
              Safety analysis will load automatically
            </div>
          )}
        </div>

        {/* Google Reviews Section */}
        <div className="border-t border-gray-200 pt-3 mt-3">
          <div className="text-lg font-semibold text-gray-800 mb-2 flex items-center gap-2">
            <span>⭐</span>
            Google Reviews
          </div>
          {reviewsData ? (
            <ReviewsDetails
              reviewsData={reviewsData}
              isExpanded={showReviewsDetails}
              onToggle={() => setShowReviewsDetails(!showReviewsDetails)}
            />
          ) : reviewsLoading ? (
            <div className="text-sm opacity-80 mb-4 text-center animate-pulse text-gray-500">
              Analyzing building reviews...
            </div>
          ) : reviewsError ? (
            <div className="bg-yellow-500/10 border border-yellow-300 text-yellow-700 rounded-lg p-2 text-xs">
              {reviewsError}
            </div>
          ) : (
            <div className="text-xs text-gray-500 italic">
              Reviews analysis will load automatically
            </div>
          )}
        </div>

        {/* Route Planning Section */}
        {address && (
          <RouteInput
            originAddress={address}
            onRouteRequest={handleRouteRequest}
            isLoading={routeLoading}
          />
        )}

        <a
          href="#"
          className="text-blue-600 hover:underline text-sm mt-2 font-medium self-start"
        >
          View details
        </a>
        {error && (
          <div className="bg-red-500/10 border border-red-300 text-red-700 rounded-lg p-3 text-sm font-medium text-center mt-2">
            {error}
          </div>
        )}
        {/* <button
          onClick={calculateEnergyCost}
          className="w-full mt-2 py-2 px-4 bg-green-600 hover:bg-green-700 text-white font-semibold rounded-lg shadow transition-colors duration-150"
        >
          Calculate
        </button> */}
      </div>
    </div>
  );
}

export default App;
