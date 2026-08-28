import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError, map } from 'rxjs/operators';

import { environment } from '../../../environments/environment';
import { ApiResponse } from '../models/auth.model';

export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, string[]>;
}

@Injectable({ providedIn: 'root' })
export class ApiClientService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = environment.apiUrl;

  get<T>(path: string, query?: Record<string, string | number | boolean | undefined>): Observable<T> {
    return this.http.get<ApiResponse<T>>(`${this.baseUrl}${path}`, { params: this.toParams(query) }).pipe(
      map((response) => keysToCamel(response.data) as T),
      catchError(this.handleError),
    );
  }

  getPaginated<T>(
    path: string,
    query?: Record<string, string | number | boolean | undefined>,
  ): Observable<{ items: T[]; total: number; page: number; pageSize: number }> {
    return this.http
      .get<{
        success: boolean;
        data: T[];
        meta: { page: number; pageSize?: number; page_size?: number; total: number };
      }>(`${this.baseUrl}${path}`, { params: this.toParams(query) })
      .pipe(
        map((response) => {
          const meta = keysToCamel(response.meta) as { page: number; pageSize: number; total: number };
          return {
            items: keysToCamel(response.data) as T[],
            total: meta.total,
            page: meta.page,
            pageSize: meta.pageSize,
          };
        }),
        catchError(this.handleError),
      );
  }

  post<T>(path: string, body: unknown): Observable<T> {
    return this.http.post<ApiResponse<T>>(`${this.baseUrl}${path}`, body).pipe(
      map((response) => keysToCamel(response.data) as T),
      catchError(this.handleError),
    );
  }

  postForm<T>(path: string, body: FormData): Observable<T> {
    return this.http.post<ApiResponse<T>>(`${this.baseUrl}${path}`, body).pipe(
      map((response) => keysToCamel(response.data) as T),
      catchError(this.handleError),
    );
  }

  getBlob(path: string): Observable<Blob> {
    return this.http.get(`${this.baseUrl}${path}`, { responseType: 'blob' }).pipe(catchError(this.handleError));
  }

  patch<T>(path: string, body: unknown = {}): Observable<T> {
    return this.http.patch<ApiResponse<T>>(`${this.baseUrl}${path}`, body).pipe(
      map((response) => keysToCamel(response.data) as T),
      catchError(this.handleError),
    );
  }

  put<T>(path: string, body: unknown): Observable<T> {
    return this.http.put<ApiResponse<T>>(`${this.baseUrl}${path}`, body).pipe(
      map((response) => keysToCamel(response.data) as T),
      catchError(this.handleError),
    );
  }

  delete<T>(path: string): Observable<T> {
    return this.http.delete<ApiResponse<T>>(`${this.baseUrl}${path}`).pipe(
      map((response) => keysToCamel(response.data) as T),
      catchError(this.handleError),
    );
  }

  private toParams(query?: Record<string, string | number | boolean | undefined>): HttpParams {
    let params = new HttpParams();
    if (query) {
      Object.entries(query).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
          params = params.set(key, String(value));
        }
      });
    }
    return params;
  }

  private handleError(error: HttpErrorResponse): Observable<never> {
    const message =
      typeof error.error?.detail === 'string'
        ? error.error.detail
        : error.error?.message || 'An unexpected error occurred. Please try again.';
    return throwError(() => ({ code: String(error.status), message } satisfies ApiError));
  }
}

function keysToCamel(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map(keysToCamel);
  }
  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>).map(([key, nested]) => [
        key.replace(/_([a-z])/g, (_, letter: string) => letter.toUpperCase()),
        keysToCamel(nested),
      ]),
    );
  }
  return value;
}
