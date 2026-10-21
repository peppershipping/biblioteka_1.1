export interface User {
  id: number;
  username: string;
  email: string | null;
}

export interface Author {
  id: number;
  name: string;
}

export interface Genre {
  id: number;
  name: string;
}

export interface Book {
  id: number;
  title: string;
  description: string;
  publication_year: number | null;
  cover_url: string | null;
  authors: Author[];
  genres: Genre[];
}

export interface BookDetail extends Book {
  status: ReadingStatus | null;
  my_rating: number | null;
}

export type ReadingStatus = "want_to_read" | "reading" | "read";

export const STATUS_LABELS: Record<ReadingStatus, string> = {
  want_to_read: "Хочу прочитать",
  reading: "Читаю",
  read: "Прочитано",
};

export interface LibraryEntry {
  id: number;
  book_id: number;
  status: ReadingStatus;
  comment: string;
  added_at: string;
  book: Book;
  rating: Rating | null;
  my_rating: number | null;
}

export interface Rating {
  id: number;
  plot: number;
  characters: number;
  style: number;
  total: number;
  updated_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}
