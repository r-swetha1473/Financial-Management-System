import { Component, EventEmitter, Input, OnChanges, OnDestroy, Output, SimpleChanges } from '@angular/core';
import { FormsModule } from '@angular/forms';

export interface FilterBarOption {
  value: string;
  label: string;
}

export interface FilterBarSelect {
  key: string;
  label: string;
  blankLabel: string;
  value: string;
  options: FilterBarOption[];
}

export interface FilterBarState {
  search: string;
  values: Record<string, string>;
}

const SEARCH_DEBOUNCE_MS = 400;

@Component({
  selector: 'app-filter-bar',
  standalone: true,
  imports: [FormsModule],
  template: `
    <div class="filter-bar">
      <div class="filter-bar__row">
        <label class="filter-bar__search">
          <svg class="filter-bar__search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <circle cx="11" cy="11" r="7" />
            <path d="m20 20-3-3" />
          </svg>
          <input
            class="form-input"
            type="search"
            [placeholder]="searchPlaceholder"
            [attr.aria-label]="searchPlaceholder"
            [(ngModel)]="draftSearch"
            (ngModelChange)="onSearchInput()"
            (keyup.enter)="flushSearch()"
          />
        </label>
        @for (select of selects; track select.key) {
          <select
            class="form-select filter-bar__select"
            [attr.aria-label]="select.label"
            [ngModel]="select.value"
            (ngModelChange)="onSelect(select.key, $event)"
          >
            <option value="">{{ select.blankLabel }}</option>
            @for (option of select.options; track option.value) {
              <option [value]="option.value">{{ option.label }}</option>
            }
          </select>
        }
        @if (hasActive) {
          <div class="filter-bar__actions">
            <button class="btn btn--ghost btn--sm" type="button" (click)="clear()">Clear filters</button>
          </div>
        }
      </div>
    </div>
  `,
})
export class FilterBarComponent implements OnChanges, OnDestroy {
  @Input() search = '';
  @Input() searchPlaceholder = 'Search...';
  @Input() selects: FilterBarSelect[] = [];
  @Output() changed = new EventEmitter<FilterBarState>();

  draftSearch = '';
  private debounceHandle: ReturnType<typeof setTimeout> | null = null;

  get hasActive(): boolean {
    return Boolean(this.draftSearch.trim()) || this.selects.some((select) => Boolean(select.value));
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['search']) {
      this.draftSearch = this.search;
    }
  }

  ngOnDestroy(): void {
    this.clearTimer();
  }

  onSearchInput(): void {
    this.clearTimer();
    this.debounceHandle = setTimeout(() => this.emitState(), SEARCH_DEBOUNCE_MS);
  }

  flushSearch(): void {
    this.clearTimer();
    this.emitState();
  }

  onSelect(key: string, value: string): void {
    this.clearTimer();
    this.emitState({ [key]: value });
  }

  clear(): void {
    this.clearTimer();
    this.draftSearch = '';
    const values: Record<string, string> = {};
    for (const select of this.selects) {
      values[select.key] = '';
    }
    this.changed.emit({ search: '', values });
  }

  private emitState(override: Record<string, string> = {}): void {
    const values: Record<string, string> = {};
    for (const select of this.selects) {
      values[select.key] = override[select.key] ?? select.value;
    }
    this.changed.emit({ search: this.draftSearch.trim(), values });
  }

  private clearTimer(): void {
    if (this.debounceHandle) {
      clearTimeout(this.debounceHandle);
      this.debounceHandle = null;
    }
  }
}
