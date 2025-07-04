import { useState } from "react";
import type { ReviewsAnalysis } from "../types/reviews";

interface ReviewsDetailsProps {
  reviewsData: ReviewsAnalysis;
  isExpanded: boolean;
  onToggle: () => void;
}

export function ReviewsDetails({ reviewsData, isExpanded, onToggle }: ReviewsDetailsProps) {
  const [activeTab, setActiveTab] = useState<"summary" | "pros-cons" | "reviews">("summary");

  const { building_info, reviews_summary, ai_analysis, recent_reviews } = reviewsData;

  const renderStars = (rating: number) => {
    return "★".repeat(Math.floor(rating)) + "☆".repeat(5 - Math.floor(rating));
  };

  const getRecommendationColor = (summary: string) => {
    const lower = summary.toLowerCase();
    if (lower.includes("highly recommended") || lower.includes("excellent")) {
      return "text-green-600 bg-green-50 border-green-200";
    } else if (lower.includes("generally positive") || lower.includes("good choice")) {
      return "text-blue-600 bg-blue-50 border-blue-200";
    } else if (lower.includes("mixed") || lower.includes("consider")) {
      return "text-yellow-600 bg-yellow-50 border-yellow-200";
    } else if (lower.includes("caution") || lower.includes("issues")) {
      return "text-orange-600 bg-orange-50 border-orange-200";
    } else if (lower.includes("not recommended") || lower.includes("poor")) {
      return "text-red-600 bg-red-50 border-red-200";
    }
    return "text-gray-600 bg-gray-50 border-gray-200";
  };

  return (
    <div className="space-y-3">
      {/* Building Rating Overview */}
      <div className="bg-gray-50 rounded-lg p-3">
        <div className="flex items-center justify-between mb-2">
          <div className="font-medium text-gray-800">{building_info.name}</div>
          <div className="text-sm text-gray-500">
            {reviews_summary.total_reviews_analyzed} recent reviews
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-lg font-semibold text-yellow-600">
            {reviews_summary.average_rating.toFixed(1)}
          </span>
          <span className="text-yellow-500">
            {renderStars(reviews_summary.average_rating)}
          </span>
          <span className="text-sm text-gray-500">
            ({building_info.total_reviews} total)
          </span>
        </div>
      </div>

      {/* AI Summary */}
      {ai_analysis.OVERALL_SUMMARY && (
        <div className={`border rounded-lg p-3 ${getRecommendationColor(ai_analysis.OVERALL_SUMMARY)}`}>
          <div className="text-sm font-medium">AI Analysis Summary</div>
          <div className="text-sm mt-1">{ai_analysis.OVERALL_SUMMARY}</div>
        </div>
      )}

      {/* Toggle Button */}
      <button
        onClick={onToggle}
        className="w-full text-left text-sm text-blue-600 hover:text-blue-800 font-medium flex items-center gap-1"
      >
        {isExpanded ? "Hide" : "Show"} detailed reviews analysis
        <span className={`transform transition-transform ${isExpanded ? "rotate-180" : ""}`}>
          ▼
        </span>
      </button>

      {/* Expanded Details */}
      {isExpanded && (
        <div className="space-y-3 border-t border-gray-200 pt-3">
          {/* Tab Navigation */}
          <div className="flex space-x-1 bg-gray-100 rounded-lg p-1">
            <button
              onClick={() => setActiveTab("summary")}
              className={`flex-1 py-1 px-2 text-xs font-medium rounded-md transition-colors ${
                activeTab === "summary"
                  ? "bg-white text-gray-900 shadow-sm"
                  : "text-gray-600 hover:text-gray-900"
              }`}
            >
              Summary
            </button>
            <button
              onClick={() => setActiveTab("pros-cons")}
              className={`flex-1 py-1 px-2 text-xs font-medium rounded-md transition-colors ${
                activeTab === "pros-cons"
                  ? "bg-white text-gray-900 shadow-sm"
                  : "text-gray-600 hover:text-gray-900"
              }`}
            >
              Pros & Cons
            </button>
            <button
              onClick={() => setActiveTab("reviews")}
              className={`flex-1 py-1 px-2 text-xs font-medium rounded-md transition-colors ${
                activeTab === "reviews"
                  ? "bg-white text-gray-900 shadow-sm"
                  : "text-gray-600 hover:text-gray-900"
              }`}
            >
              Recent Reviews
            </button>
          </div>

          {/* Tab Content */}
          {activeTab === "summary" && (
            <div className="space-y-3">
              {ai_analysis.LIVING_EXPERIENCE && (
                <div>
                  <div className="text-sm font-medium text-gray-800 mb-1">Living Experience</div>
                  <div className="text-sm text-gray-600 bg-gray-50 rounded-lg p-2">
                    {ai_analysis.LIVING_EXPERIENCE}
                  </div>
                </div>
              )}
              
              {ai_analysis.KEY_THEMES && ai_analysis.KEY_THEMES.length > 0 && (
                <div>
                  <div className="text-sm font-medium text-gray-800 mb-1">Key Themes</div>
                  <div className="flex flex-wrap gap-1">
                    {ai_analysis.KEY_THEMES.map((theme, index) => (
                      <span
                        key={index}
                        className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded-full"
                      >
                        {theme}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {ai_analysis.RECOMMENDATIONS && ai_analysis.RECOMMENDATIONS.length > 0 && (
                <div>
                  <div className="text-sm font-medium text-gray-800 mb-1">Recommendations</div>
                  <ul className="text-sm text-gray-600 space-y-1">
                    {ai_analysis.RECOMMENDATIONS.map((rec, index) => (
                      <li key={index} className="flex items-start gap-2">
                        <span className="text-blue-500 mt-0.5">•</span>
                        <span>{rec}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {activeTab === "pros-cons" && (
            <div className="grid grid-cols-1 gap-3">
              {ai_analysis.PROS && ai_analysis.PROS.length > 0 && (
                <div>
                  <div className="text-sm font-medium text-green-700 mb-2 flex items-center gap-1">
                    <span>👍</span> Pros
                  </div>
                  <ul className="space-y-1">
                    {ai_analysis.PROS.map((pro, index) => (
                      <li key={index} className="text-sm text-gray-600 flex items-start gap-2">
                        <span className="text-green-500 mt-0.5">+</span>
                        <span>{pro}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {ai_analysis.CONS && ai_analysis.CONS.length > 0 && (
                <div>
                  <div className="text-sm font-medium text-red-700 mb-2 flex items-center gap-1">
                    <span>👎</span> Cons
                  </div>
                  <ul className="space-y-1">
                    {ai_analysis.CONS.map((con, index) => (
                      <li key={index} className="text-sm text-gray-600 flex items-start gap-2">
                        <span className="text-red-500 mt-0.5">-</span>
                        <span>{con}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {activeTab === "reviews" && (
            <div className="space-y-3">
              {recent_reviews && recent_reviews.length > 0 ? (
                recent_reviews.slice(0, 3).map((review, index) => (
                  <div key={index} className="bg-gray-50 rounded-lg p-3">
                    <div className="flex items-center justify-between mb-2">
                      <div className="font-medium text-sm text-gray-800">{review.author}</div>
                      <div className="flex items-center gap-1">
                        <span className="text-yellow-500 text-sm">
                          {renderStars(review.rating)}
                        </span>
                        <span className="text-xs text-gray-500">{review.relative_time}</span>
                      </div>
                    </div>
                    <div className="text-sm text-gray-600">
                      {review.text.length > 150 
                        ? `${review.text.substring(0, 150)}...` 
                        : review.text
                      }
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-sm text-gray-500 italic text-center py-4">
                  No recent reviews available
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
} 