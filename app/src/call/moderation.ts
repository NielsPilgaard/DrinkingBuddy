import { blockEndpointBlockPost, reportEndpointReportPost } from '../api/generated/sdk.gen';
import type { ReportBody } from '../api/generated/types.gen';

export type ReportReason = ReportBody['reason'];

export const REPORT_REASONS: { value: ReportReason; label: string; hint?: string }[] = [
  { value: 'nudity', label: 'Nudity' },
  { value: 'harassment', label: 'Harassment' },
  { value: 'underage', label: 'Underage user' },
  {
    value: 'csam',
    label: 'Sexual content involving a minor',
    // Capturing it would put abuse material on the reporter's own device
    // (docs/csam-runbook.md). We escalate from the report alone.
    hint: "Don't screenshot or record it. Your report is enough, and we escalate it right away.",
  },
  { value: 'spam', label: 'Spam' },
  { value: 'other', label: 'Other' },
];

export async function reportUser(
  reportedId: string,
  callSessionId: string,
  reason: ReportReason,
): Promise<void> {
  await reportEndpointReportPost({
    body: { reported_id: reportedId, call_session_id: callSessionId, reason },
  });
}

export async function blockUser(blockedId: string): Promise<void> {
  await blockEndpointBlockPost({ body: { blocked_id: blockedId } });
}
