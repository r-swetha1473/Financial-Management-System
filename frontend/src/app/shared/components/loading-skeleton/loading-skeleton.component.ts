import { Component, Input } from '@angular/core';

@Component({
  selector: 'app-loading-skeleton',
  standalone: true,
  template: `
    <div class="loading-skeleton">
      @for (row of rows; track $index) {
        <div class="skeleton skeleton--text" [style.width]="row"></div>
      }
    </div>
  `,
})
export class LoadingSkeletonComponent {
  @Input() rows = ['70%', '90%', '55%'];
}
