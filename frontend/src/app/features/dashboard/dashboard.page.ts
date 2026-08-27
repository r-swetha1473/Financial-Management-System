import {
  AfterViewInit,
  Component,
  ElementRef,
  OnDestroy,
  ViewChild,
  inject,
  signal,
} from '@angular/core';
import { Chart, ChartConfiguration, registerables } from 'chart.js';
import { forkJoin } from 'rxjs';

import { DashboardApiService } from '../../core/api/dashboard-api.service';
import { AuthService } from '../../core/auth/auth.service';
import {
  CashPositionItem,
  DashboardCategoryBreakdown,
  DashboardPeriod,
  DashboardSummary,
  DashboardTrendPoint,
  ProductFinancialSummary,
  RecentExpenseRow,
  RecentInvoiceRow,
  RecentReceiptRow,
} from '../../core/models/dashboard.model';
import { InrPipe } from '../../shared/pipes/inr.pipe';
import { StatusBadgeComponent } from '../../shared/components/status-badge/status-badge.component';
import { SummaryCardComponent } from '../../shared/components/summary-card/summary-card.component';
import { LoadingSkeletonComponent } from '../../shared/components/loading-skeleton/loading-skeleton.component';

Chart.register(...registerables);

@Component({
  selector: 'app-dashboard-page',
  standalone: true,
  imports: [InrPipe, StatusBadgeComponent, SummaryCardComponent, LoadingSkeletonComponent],
  templateUrl: './dashboard.page.html',
})
export class DashboardPage implements AfterViewInit, OnDestroy {
  private readonly api = inject(DashboardApiService);
  private readonly auth = inject(AuthService);

  @ViewChild('trendCanvas') trendCanvas?: ElementRef<HTMLCanvasElement>;
  @ViewChild('categoryCanvas') categoryCanvas?: ElementRef<HTMLCanvasElement>;

  readonly periods: DashboardPeriod[] = ['daily', 'weekly', 'monthly'];
  readonly loading = signal(true);
  readonly error = signal('');
  readonly period = signal<DashboardPeriod>('monthly');
  readonly session = this.auth.session;

  summary: DashboardSummary | null = null;
  trend: DashboardTrendPoint[] = [];
  categories: DashboardCategoryBreakdown[] = [];
  expenses: RecentExpenseRow[] = [];
  invoices: RecentInvoiceRow[] = [];
  receipts: RecentReceiptRow[] = [];
  cashPosition: CashPositionItem[] = [];
  products: ProductFinancialSummary[] = [];

  private trendChart?: Chart;
  private categoryChart?: Chart;
  private viewReady = false;

  ngAfterViewInit(): void {
    this.viewReady = true;
    this.load();
  }

  ngOnDestroy(): void {
    this.trendChart?.destroy();
    this.categoryChart?.destroy();
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
      categories: this.api.getExpenseCategories(),
      expenses: this.api.getRecentExpenses(),
      invoices: this.api.getRecentInvoices(),
      receipts: this.api.getRecentReceipts(),
      cashPosition: this.api.getCashPosition(),
      products: this.api.getProductSummaries(),
    }).subscribe({
      next: (data) => {
        this.summary = data.summary;
        this.trend = data.trend;
        this.categories = data.categories;
        this.expenses = data.expenses;
        this.invoices = data.invoices;
        this.receipts = data.receipts;
        this.cashPosition = data.cashPosition;
        this.products = data.products;
        this.loading.set(false);
        setTimeout(() => this.renderCharts());
      },
      error: () => {
        this.loading.set(false);
        this.error.set('Unable to load dashboard data.');
      },
    });
  }

  private renderCharts(): void {
    if (!this.viewReady) {
      return;
    }
    this.renderTrendChart();
    this.renderCategoryChart();
  }

  private renderTrendChart(): void {
    if (!this.trendCanvas) {
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

  private renderCategoryChart(): void {
    if (!this.categoryCanvas) {
      return;
    }
    this.categoryChart?.destroy();
    this.categoryChart = new Chart(this.categoryCanvas.nativeElement, {
      type: 'doughnut',
      data: {
        labels: this.categories.map((item) => item.category),
        datasets: [
          {
            data: this.categories.map((item) => Number(item.amount)),
            backgroundColor: ['#0d9488', '#2563eb', '#d97706', '#7c3aed', '#64748b'],
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: 'bottom' } },
      },
    });
  }
}
