import { Injectable, inject } from '@angular/core';
import { Observable, of } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { environment } from '../../../environments/environment';
import { ApiClientService } from './api-client.service';
import {
  CashPositionItem,
  DashboardPeriod,
  DashboardSummary,
  DashboardTrendPoint,
  ProductFinancialSummary,
  RecentExpenseRow,
  RecentInvoiceRow,
  RecentReceiptRow,
} from '../models/dashboard.model';
import { DASHBOARD_SEED } from '../seed/dev-seed';

@Injectable({ providedIn: 'root' })
export class DashboardApiService {
  private readonly api = inject(ApiClientService);

  getSummary(): Observable<DashboardSummary> {
    return this.api.get<DashboardSummary>('/dashboard/summary');
  }

  getTrend(period: DashboardPeriod): Observable<DashboardTrendPoint[]> {
    return this.withFallback(
      this.api.get<DashboardTrendPoint[]>('/dashboard/income', { period }),
      DASHBOARD_SEED.trend(period),
    );
  }

  getRecentExpenses(): Observable<RecentExpenseRow[]> {
    return this.withFallback(this.api.get<RecentExpenseRow[]>('/dashboard/expenses'), DASHBOARD_SEED.expenses);
  }

  getRecentInvoices(): Observable<RecentInvoiceRow[]> {
    return this.withFallback(this.api.get<RecentInvoiceRow[]>('/dashboard/invoices'), DASHBOARD_SEED.invoices);
  }

  getRecentReceipts(): Observable<RecentReceiptRow[]> {
    return this.withFallback(this.api.get<RecentReceiptRow[]>('/dashboard/receipts'), DASHBOARD_SEED.receipts);
  }

  getCashPosition(): Observable<CashPositionItem[]> {
    return this.api.get<CashPositionItem[]>('/dashboard/cash-position');
  }

  getProductSummaries(): Observable<ProductFinancialSummary[]> {
    return this.withFallback(
      this.api.get<ProductFinancialSummary[]>('/dashboard/products'),
      DASHBOARD_SEED.products,
    );
  }

  private withFallback<T>(request$: Observable<T>, seed: T): Observable<T> {
    if (!environment.useDevSeed) {
      return request$;
    }
    return request$.pipe(catchError(() => of(seed)));
  }
}
