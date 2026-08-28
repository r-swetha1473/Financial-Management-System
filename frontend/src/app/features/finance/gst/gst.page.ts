import { Component, OnInit, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { LoadingSkeletonComponent } from '../../../shared/components/loading-skeleton/loading-skeleton.component';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';
import { SummaryCardComponent } from '../../../shared/components/summary-card/summary-card.component';
import { InrPipe } from '../../../shared/pipes/inr.pipe';
import { FinanceBannerComponent } from '../components/finance-banner.component';
import { GstSummary } from '../models/finance.model';
import { FinanceApiService } from '../services/finance-api.service';

@Component({
  selector: 'app-gst-page',
  standalone: true,
  imports: [RouterLink, PageHeaderComponent, FinanceBannerComponent, SummaryCardComponent, LoadingSkeletonComponent, InrPipe],
  templateUrl: './gst.page.html',
})
export class GstPage implements OnInit {
  private readonly api = inject(FinanceApiService);
  readonly loading = signal(true);
  readonly error = signal('');
  gst: GstSummary | null = null;

  ngOnInit(): void {
    this.api.getGstSummary().subscribe({
      next: (gst) => {
        this.gst = gst;
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.error.set('Unable to load GST summary.');
      },
    });
  }
}
