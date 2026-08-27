import { Component, OnInit, inject } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { DocumentTrailComponent } from '../../../shared/components/document-trail/document-trail.component';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';
import { InrPipe } from '../../../shared/pipes/inr.pipe';
import { InvoiceReceipt } from '../../o2c/models/o2c.model';
import { O2cApiService } from '../../o2c/services/o2c-api.service';
import { ExistingSalesBannerComponent } from '../components/existing-sales-banner.component';

@Component({
  selector: 'app-receipt-detail-page',
  standalone: true,
  imports: [RouterLink, PageHeaderComponent, ExistingSalesBannerComponent, DocumentTrailComponent, EmptyStateComponent, InrPipe],
  templateUrl: './receipt-detail.page.html',
})
export class ReceiptDetailPage implements OnInit {
  private readonly api = inject(O2cApiService);
  private readonly route = inject(ActivatedRoute);
  record: InvoiceReceipt | null = null;

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id') ?? '';
    this.api.getReceipt(id).subscribe((record) => (this.record = record));
  }
}
