export interface ReviewsAnalysis {
  building_info: {
    name: string;
    address: string;
    place_id: string;
    rating: number;
    total_reviews: number;
  };
  reviews_summary: {
    total_reviews_analyzed: number;
    average_rating: number;
    rating_distribution: { [key: string]: number };
    analysis_period: string;
    last_updated: string;
  };
  ai_analysis: {
    OVERALL_SUMMARY: string;
    PROS: string[];
    CONS: string[];
    KEY_THEMES: string[];
    LIVING_EXPERIENCE: string;
    RECOMMENDATIONS: string[];
  };
  recent_reviews: ReviewItem[];
  data_source: string;
  analysis_timestamp: string;
  status?: string;
  message?: string;
}

export interface ReviewItem {
  author: string;
  rating: number;
  text: string;
  date: string;
  relative_time: string;
  author_url?: string;
} 