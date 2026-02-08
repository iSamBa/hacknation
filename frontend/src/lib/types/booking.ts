export interface BookingListItem {
  id: string;
  user_id: string;
  status: string;
  service_type: string;
  preferred_date: string | null;
  preferred_time: string | null;
  location_override: string | null;
  raw_message: string;
  created_at: string;
  updated_at: string;
  provider_count: number;
  called_count: number;
}

export interface ShortlistItem {
  rank: number | null;
  provider_name: string;
  provider_phone: string | null;
  place_id: string;
  rating: number;
  review_count: number;
  travel_minutes: number | null;
  pre_score: number;
  provider_id: string;
  was_called: boolean;
}

export interface BookingDetail {
  id: string;
  status: string;
  service_type: string;
  preferred_date: string | null;
  preferred_time: string | null;
  location_override: string | null;
  raw_message: string;
  created_at: string;
}
