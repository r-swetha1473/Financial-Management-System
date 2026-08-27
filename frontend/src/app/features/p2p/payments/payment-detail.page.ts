import { Component, OnInit, inject } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { DocumentTrailComponent } from '../../../shared/components/document-trail/document-trail.component';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';
import { StatusBadgeComponent } from '../../../shared/components/status-badge/status-badge.component';
import { InrPipe } from '../../../shared/pipes/inr.pipe';
import { P2pBannerComponent } from '../components/p2p-banner.component';
import { SupplierPayment } from '../models/p2p.model';
import { P2pApiService } from '../services/p2p-api.service';

@Component({
  selector: 'app-payment-detail-page',
  standalone: true,
  imports: [RouterLink, PageHeaderComponent, P2pBannerComponent, StatusBadgeComponent, DocumentTrailComponent, EmptyStateComponent, InrPipe],
  templateUrl: './payment-detail.page.html',
})
export class PaymentDetailPage implements OnInit {
  private readonly api = inject(P2pApiService);
  private readonly route = inject(ActivatedRoute);
  record: SupplierPayment | null = null;

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id') ?? '';
    this.api.getPayment(id).subscribe({
      next: (record) => (this.record = record),
      error: () => (this.record = null),
    });
  }
}
