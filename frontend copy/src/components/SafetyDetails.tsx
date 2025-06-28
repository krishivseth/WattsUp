import { type JSX } from "react";

interface ComplaintCategory {
  count: number;
  percentage: number;
  description: string;
  top_complaints: Record<string, number>;
}

interface SafetyDetailsProps {
  summary: string;
  complaintBreakdown: Record<string, ComplaintCategory>;
  recommendations: string[];
  recentActivity: {
    recent_complaints: number;
    trend: string;
    days_analyzed: number;
  };
  isExpanded: boolean;
  onToggle: () => void;
}

export const SafetyDetails = ({
  summary,
  complaintBreakdown,
  recommendations,
  recentActivity,
  isExpanded,
  onToggle
}: SafetyDetailsProps): JSX.Element => {
  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'increasing': return '📈';
      case 'decreasing': return '📉';
      case 'stable': return '➡️';
      default: return '➡️';
    }
  };

  const getTrendColor = (trend: string) => {
    switch (trend) {
      case 'increasing': return 'text-red-600';
      case 'decreasing': return 'text-green-600';
      case 'stable': return 'text-gray-600';
      default: return 'text-gray-600';
    }
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'HIGH_CONCERN': return '🚨';
      case 'MEDIUM_CONCERN': return '⚠️';
      case 'LOW_CONCERN': return '🟡';
      case 'INFRASTRUCTURE': return '🔧';
      default: return '📊';
    }
  };

  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'HIGH_CONCERN': return 'border-red-200 bg-red-50';
      case 'MEDIUM_CONCERN': return 'border-orange-200 bg-orange-50';
      case 'LOW_CONCERN': return 'border-yellow-200 bg-yellow-50';
      case 'INFRASTRUCTURE': return 'border-blue-200 bg-blue-50';
      default: return 'border-gray-200 bg-gray-50';
    }
  };

  return (
    <div className="space-y-3">
      <button
        onClick={onToggle}
        className="w-full text-left bg-white border border-gray-200 rounded-lg p-3 hover:bg-gray-50 transition-colors duration-150"
      >
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-gray-700">Safety Details</span>
          <span className="text-gray-400 text-sm">
            {isExpanded ? '▼' : '▶'}
          </span>
        </div>
        <p className="text-xs text-gray-600 mt-1 line-clamp-2">
          {summary}
        </p>
      </button>

      {isExpanded && (
        <div className="space-y-4 bg-white border border-gray-200 rounded-lg p-4">
          {/* Summary */}
          <div>
            <h4 className="text-sm font-semibold text-gray-800 mb-2">Area Summary</h4>
            <p className="text-xs text-gray-700 leading-relaxed">{summary}</p>
          </div>

          {/* Recent Activity */}
          <div>
            <h4 className="text-sm font-semibold text-gray-800 mb-2">Recent Activity</h4>
            <div className="flex items-center gap-2 text-xs">
              <span className="text-lg">{getTrendIcon(recentActivity.trend)}</span>
              <span className={`font-medium ${getTrendColor(recentActivity.trend)}`}>
                {recentActivity.recent_complaints} complaints in last {recentActivity.days_analyzed} days
              </span>
              <span className="text-gray-500">
                ({recentActivity.trend} trend)
              </span>
            </div>
          </div>

          {/* Complaint Breakdown */}
          {Object.keys(complaintBreakdown).length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-gray-800 mb-2">Complaint Categories</h4>
              <div className="space-y-2">
                {Object.entries(complaintBreakdown).map(([category, data]) => (
                  <div 
                    key={category} 
                    className={`border rounded-lg p-2 ${getCategoryColor(category)}`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-1">
                        <span className="text-sm">{getCategoryIcon(category)}</span>
                        <span className="text-xs font-medium text-gray-800">
                          {category.replace('_', ' ').toLowerCase().replace(/^./, str => str.toUpperCase())}
                        </span>
                      </div>
                      <span className="text-xs font-semibold text-gray-700">
                        {data.count} ({data.percentage.toFixed(0)}%)
                      </span>
                    </div>
                    <p className="text-xs text-gray-600 mb-1">{data.description}</p>
                    {Object.keys(data.top_complaints).length > 0 && (
                      <div className="text-xs text-gray-500">
                        Top: {Object.entries(data.top_complaints)
                          .slice(0, 2)
                          .map(([complaint, count]) => `${complaint} (${count})`)
                          .join(', ')}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Recommendations */}
          {recommendations.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-gray-800 mb-2">Safety Recommendations</h4>
              <ul className="space-y-1">
                {recommendations.slice(0, 3).map((rec, index) => (
                  <li key={index} className="flex items-start gap-2 text-xs text-gray-700">
                    <span className="text-blue-500 mt-0.5">•</span>
                    <span>{rec}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}; 