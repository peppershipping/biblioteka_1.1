export type ReadingStatus = "want_to_read" | "in_progress" | "read";

export const STATUS_LABELS: Record<ReadingStatus, string> = {
  want_to_read: "Хочу прочитать",
  in_progress: "В процессе",
  read: "Прочитано",
};

export const STATUSES: ReadingStatus[] = ["want_to_read", "in_progress", "read"];

export interface User {
  id: number;
  username: string;
  email: string;
  role: "user" | "admin";
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface Page<T> {
  items: T[];
  limit: number;
  offset: number;
  total: number;
}

export interface Book {
  id: number;
  title: string;
  description: string | null;
  publication_year: number | null;
  cover_url: string | null;
  authors: string[];
  genres: string[];
}

export interface BookListItem extends Book {
  my_status: ReadingStatus | null;
  my_rating: number | null;
}

export interface Interpreted {
  q: string | null;
  genre: string | null;
  year: number | null;
}

export interface BookPage extends Page<BookListItem> {
  interpreted: Interpreted | null;
}

export interface BookDetail extends BookListItem {
  library_id: number | null;
  avg_rating: number | null;
  ratings_count: number;
}

export interface Rating {
  plot: number;
  characters: number;
  style: number;
  total: number;
  updated_at: string;
}

export interface PublicRating extends Rating {
  username: string;
}

export interface LibraryItem {
  id: number;
  book_id: number;
  status: ReadingStatus;
  added_at: string;
  book: Book;
  rating: Rating | null;
}

export interface LibraryStats {
  total: number;
  want_to_read: number;
  in_progress: number;
  read: number;
  ratings_count: number;
  avg_rating: number | null;
}

export type Feedback = "helpful" | "not_helpful";

export interface Recommendation {
  id: number;
  book: Book;
  reason: string | null;
  score: number | null;
  signals: { similar_to: string | null; genres: string[] };
  feedback: Feedback | null;
}

export interface RecommendationsPage extends Page<Recommendation> {
  personalized: boolean;
  ratings_count: number;
  min_ratings: number;
  message: string | null;
  explanations: boolean;
}

export interface Genre {
  id: number;
  name: string;
}
