export interface SafetyRating {
  score: number;
  grade: string;
  description: string;
  color: string;
}

export interface SafetyMetrics {
  total_complaints: number;
  weighted_safety_score: number;
  complaints_per_day: number;
  high_concern_ratio: number;
  category_distribution: Record<string, number>;
}

export interface ComplaintCategory {
  count: number;
  percentage: number;
  description: string;
  top_complaints: Record<string, number>;
}

export interface RecentActivity {
  recent_complaints: number;
  previous_period_complaints: number;
  trend: 'increasing' | 'decreasing' | 'stable';
  days_analyzed: number;
}

export interface AreaInfo {
  zip_code?: string;
  borough?: string;
  address?: string;
  radius_miles: number;
  data_points: number;
}

export interface SafetyAnalysis {
  area_info: AreaInfo;
  safety_rating: SafetyRating;
  safety_metrics: SafetyMetrics;
  safety_summary: string;
  complaint_breakdown: Record<string, ComplaintCategory>;
  recent_activity: RecentActivity;
  recommendations: string[];
}

export interface SafetyApiResponse extends SafetyAnalysis {}

export interface BoroughComparison {
  [borough: string]: {
    safety_score: number;
    grade: string;
    total_complaints: number;
    high_concern_ratio: number;
  };
} 