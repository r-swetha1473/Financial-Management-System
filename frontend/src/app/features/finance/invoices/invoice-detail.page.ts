import { Component, OnInit, computed, inject } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';

import { AuthService } from '../../../core/auth/auth.service';
import { hasPermission } from '../../../core/rbac/permissions';
import { DocumentTrailComponent } from '../../../shared/components/document-trail/document-trail.component';
import { EmptyStateComponent } from '../../../shared/components/empty-state/empty-state.component';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';
import { StatusBadgeComponent } from '../../../shared/components/status-badge/status-badge.component';
import { InrPipe } from '../../../shared/pipes/inr.pipe';
import { InvoiceReceipt, LegacyInvoice } from '../../o2c/models/o2c.model';
import { O2cApiService } from '../../o2c/services/o2c-api.service';
import { ExistingSalesBannerComponent } from '../components/existing-sales-banner.component';

@Component({
  selector: 'app-invoice-detail-page',
  standalone: true,
  imports: [RouterLink, PageHeaderComponent, ExistingSalesBannerComponent, StatusBadgeComponent, DocumentTrailComponent, EmptyStateComponent, InrPipe],
  templateUrl: './invoice-detail.page.html',
})
export class InvoiceDetailPage implements OnInit {
  private readonly api = inject(O2cApiService);
  private readonly route = inject(ActivatedRoute);
  private readonly auth = inject(AuthService);
  readonly canEdit = computed(() => hasPermission(this.auth.session()?.role, 'create'));
  record: LegacyInvoice | null = null;
  receipts: InvoiceReceipt[] = [];
  outstanding = '0.00';

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id') ?? '';
    forkJoin({ record: this.api.getInvoice(id), receipts: this.api.listReceipts({ pageSize: 50 }) }).subscribe((data) => {
      this.record = data.record;
      this.receipts = data.receipts.items.filter((row) => row.invoiceId === id);
      this.outstanding = this.api.legacyInvoiceOutstanding(id)?.outstanding ?? '0.00';
    });
  }
}
