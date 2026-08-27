import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

import { NAV_SECTIONS, P2P_WORKFLOW_STEPS } from '../../core/navigation/nav.config';
import { PageHeaderComponent } from '../../shared/components/page-header/page-header.component';

@Component({
  selector: 'app-p2p-overview-page',
  standalone: true,
  imports: [RouterLink, PageHeaderComponent],
  templateUrl: './p2p-overview.page.html',
})
export class P2pOverviewPage {
  readonly steps = P2P_WORKFLOW_STEPS;
  readonly items = [
    { label: 'Vendors', route: '/master/vendors' },
    ...(NAV_SECTIONS.find((section) => section.module === 'p2p')?.items ?? []),
  ];
}
