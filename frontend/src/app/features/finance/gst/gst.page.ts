import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';
import { SummaryCardComponent } from '../../../shared/components/summary-card/summary-card.component';
import { InrPipe } from '../../../shared/pipes/inr.pipe';
import { FinanceBannerComponent } from '../components/finance-banner.component';
import { ReportService } from '../services/report.service';

@Component({
  selector: 'app-gst-page',
  standalone: true,
  imports: [RouterLink, PageHeaderComponent, FinanceBannerComponent, SummaryCardComponent, InrPipe],
  templateUrl: './gst.page.html',
})
export class GstPage {
  private readonly reports = inject(ReportService);
  readonly gst = this.reports.gstTotals();
}
