import {
  AfterViewInit,
  Component,
  ElementRef,
  OnDestroy,
  ViewChild,
  inject,
  signal,
} from '@angular/core';
import { RouterLink } from '@angular/router';
import { Chart, ChartConfiguration, registerables } from 'chart.js';
import { forkJoin } from 'rxjs';

import { DashboardApiService } from '../../core/api/dashboard-api.service';
import { AuthService } from '../../core/auth/auth.service';
import {
  CashPositionItem,
  DashboardPeriod,
  DashboardSummary,
  DashboardTrendPoint,
  RecentExpenseRow,
  RecentInvoiceRow,
  RecentReceiptRow,
} from '../../core/models/dashboard.model';
import { EmptyStateComponent } from '../../shared/components/empty-state/empty-state.component';
import { LoadingSkeletonComponent } from '../../shared/components/loading-skeleton/loading-skeleton.component';
import { StatusBadgeComponent } from '../../shared/components/status-badge/status-badge.component';
import { SummaryCardComponent } from '../../shared/components/summary-card/summary-card.component';
import { InrPipe } from '../../shared/pipes/inr.pipe';

Chart.register(...registerables);

@Component({
  selector: 'app-dashboard-page',
  standalone: true,
  imports: [
    RouterLink,
    InrPipe,
    SummaryCardComponent,
    LoadingSkeletonComponent,
    EmptyStateComponent,
    StatusBadgeComponent,
  ],
  templateUrl: './dashboard.page.html',
})
export class DashboardPage implements AfterViewInit, OnDestroy {
  private readonly api = inject(DashboardApiService);
  private readonly auth = inject(AuthService);

  @ViewChild('trendCanvas') trendCanvas?: ElementRef<HTMLCanvasElement>;

  readonly periods: DashboardPeriod[] = ['daily', 'weekly', 'monthly'];
  readonly loading = signal(true);
  readonly error = signal('');
  readonly period = signal<DashboardPeriod>('monthly');
  readonly session = this.auth.session;

  summary: DashboardSummary | null = null;
  trend: DashboardTrendPoint[] = [];
  cashPosition: CashPositionItem[] = [];
  expenses: RecentExpenseRow[] = [];
  invoices: RecentInvoiceRow[] = [];
  receipts: RecentReceiptRow[] = [];

  private trendChart?: Chart;
  private viewReady = false;

  ngAfterViewInit(): void {
    this.viewReady = true;
    this.load();
  }

  ngOnDestroy(): void {
    this.trendChart?.destroy();
  }

  setPeriod(period: DashboardPeriod): void {
    this.period.set(period);
    this.api.getTrend(period).subscribe((trend) => {
      this.trend = trend;
      this.renderTrendChart();
    });
  }

  private load(): void {
    this.loading.set(true);
    this.error.set('');
    forkJoin({
      summary: this.api.getSummary(),
      trend: this.api.getTrend(this.period()),
      cashPosition: this.api.getCashPosition(),
      expenses: this.api.getRecentExpenses(),
      invoices: this.api.getRecentInvoices(),
      receipts: this.api.getRecentReceipts(),
    }).subscribe({
      next: (data) => {
        this.summary = data.summary;
        this.trend = data.trend;
        this.cashPosition = data.cashPosition;
        this.expenses = data.expenses;
        this.invoices = data.invoices;
        this.receipts = data.receipts;
        this.loading.set(false);
        setTimeout(() => this.renderTrendChart());
      },
      error: () => {
        this.loading.set(false);
        this.error.set('Unable to load dashboard data.');
      },
    });
  }

  private renderTrendChart(): void {
    if (!this.viewReady || !this.trendCanvas) {
      return;
    }
    this.trendChart?.destroy();
    const config: ChartConfiguration<'bar'> = {
      type: 'bar',
      data: {
        labels: this.trend.map((point) => point.label),
        datasets: [
          {
            label: 'Income',
            data: this.trend.map((point) => Number(point.income)),
            backgroundColor: '#059669',
            borderRadius: 6,
          },
          {
            label: 'Expenses',
            data: this.trend.map((point) => Number(point.expenses)),
            backgroundColor: '#dc2626',
            borderRadius: 6,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: 'top' } },
        scales: { y: { beginAtZero: true, ticks: { callback: (value) => `₹${value}` } } },
      },
    };
    this.trendChart = new Chart(this.trendCanvas.nativeElement, config);
  }
}
