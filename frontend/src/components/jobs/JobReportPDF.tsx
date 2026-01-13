/**
 * Pipeline One - Job Report PDF component
 * Generates a PDF document for job reports
 */

import {
  Document,
  Page,
  Text,
  View,
  StyleSheet,
} from '@react-pdf/renderer';
import type { Job, JobResults } from '../../types/job';
import { ALL_PIPELINE_STAGES, STAGE_INFO } from '../../types/job';

// PDF Styles
const styles = StyleSheet.create({
  page: {
    padding: 40,
    fontSize: 10,
    fontFamily: 'Helvetica',
    backgroundColor: '#ffffff',
  },
  header: {
    marginBottom: 20,
    borderBottom: '2px solid #3b82f6',
    paddingBottom: 15,
  },
  title: {
    fontSize: 24,
    fontFamily: 'Helvetica-Bold',
    color: '#1e293b',
    marginBottom: 5,
  },
  subtitle: {
    fontSize: 10,
    color: '#64748b',
  },
  statusBadge: {
    marginTop: 10,
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 12,
    alignSelf: 'flex-start',
  },
  statusText: {
    fontSize: 10,
    fontFamily: 'Helvetica-Bold',
    textTransform: 'uppercase',
  },
  section: {
    marginBottom: 20,
  },
  sectionTitle: {
    fontSize: 12,
    fontFamily: 'Helvetica-Bold',
    color: '#1e293b',
    marginBottom: 10,
    paddingBottom: 5,
    borderBottom: '1px solid #e2e8f0',
  },
  statsGrid: {
    flexDirection: 'row',
    gap: 10,
    marginBottom: 15,
  },
  statBox: {
    flex: 1,
    backgroundColor: '#f8fafc',
    padding: 12,
    borderRadius: 6,
    alignItems: 'center',
    border: '1px solid #e2e8f0',
  },
  statValue: {
    fontSize: 18,
    fontFamily: 'Helvetica-Bold',
    color: '#3b82f6',
  },
  statLabel: {
    fontSize: 8,
    color: '#64748b',
    marginTop: 4,
    textTransform: 'uppercase',
  },
  table: {
    borderWidth: 1,
    borderColor: '#e2e8f0',
    borderRadius: 4,
  },
  tableRow: {
    flexDirection: 'row',
    borderBottomWidth: 1,
    borderBottomColor: '#e2e8f0',
  },
  tableRowLast: {
    flexDirection: 'row',
  },
  tableLabel: {
    width: '40%',
    padding: 8,
    backgroundColor: '#f8fafc',
    color: '#64748b',
    fontSize: 9,
  },
  tableValue: {
    width: '60%',
    padding: 8,
    color: '#1e293b',
    fontSize: 9,
  },
  fileItem: {
    padding: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#e2e8f0',
  },
  fileName: {
    fontSize: 10,
    color: '#1e293b',
    fontFamily: 'Helvetica-Bold',
  },
  filePath: {
    fontSize: 8,
    color: '#64748b',
    marginTop: 2,
  },
  tag: {
    backgroundColor: '#dbeafe',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
    marginRight: 6,
    marginBottom: 6,
  },
  tagText: {
    fontSize: 9,
    color: '#1e40af',
  },
  tagsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
  },
  stagesRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10,
  },
  stageItem: {
    alignItems: 'center',
  },
  stageCircle: {
    width: 28,
    height: 28,
    borderRadius: 14,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 4,
  },
  stageNumber: {
    fontSize: 10,
    fontFamily: 'Helvetica-Bold',
    color: '#ffffff',
  },
  stageName: {
    fontSize: 7,
    color: '#64748b',
  },
  stageConnector: {
    width: 30,
    height: 2,
    backgroundColor: '#e2e8f0',
  },
  progressBarContainer: {
    backgroundColor: '#e2e8f0',
    height: 8,
    borderRadius: 4,
    marginTop: 10,
  },
  progressBar: {
    height: 8,
    borderRadius: 4,
    backgroundColor: '#3b82f6',
  },
  progressText: {
    fontSize: 8,
    color: '#64748b',
    marginTop: 4,
    textAlign: 'right',
  },
  errorBox: {
    backgroundColor: '#fef2f2',
    border: '1px solid #fecaca',
    borderRadius: 4,
    padding: 12,
  },
  errorText: {
    fontSize: 9,
    color: '#dc2626',
  },
  footer: {
    position: 'absolute',
    bottom: 30,
    left: 40,
    right: 40,
    flexDirection: 'row',
    justifyContent: 'space-between',
    borderTop: '1px solid #e2e8f0',
    paddingTop: 10,
  },
  footerText: {
    fontSize: 8,
    color: '#94a3b8',
  },
  detectionBar: {
    marginBottom: 8,
  },
  detectionLabel: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 2,
  },
  detectionClass: {
    fontSize: 9,
    color: '#1e293b',
  },
  detectionCount: {
    fontSize: 9,
    color: '#64748b',
  },
  detectionBarBg: {
    backgroundColor: '#e2e8f0',
    height: 6,
    borderRadius: 3,
  },
  detectionBarFill: {
    height: 6,
    borderRadius: 3,
    backgroundColor: '#3b82f6',
  },
});

const statusColors: Record<string, { bg: string; text: string }> = {
  pending: { bg: '#fef3c7', text: '#d97706' },
  running: { bg: '#dbeafe', text: '#2563eb' },
  paused: { bg: '#ffedd5', text: '#ea580c' },
  completed: { bg: '#dcfce7', text: '#16a34a' },
  failed: { bg: '#fee2e2', text: '#dc2626' },
  cancelled: { bg: '#f3f4f6', text: '#6b7280' },
};

function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return 'N/A';
  return new Date(dateStr).toLocaleString();
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  if (mins < 60) return `${mins}m ${secs.toFixed(0)}s`;
  const hours = Math.floor(mins / 60);
  const remainingMins = mins % 60;
  return `${hours}h ${remainingMins}m`;
}

interface JobReportPDFProps {
  job: Job;
  results?: JobResults;
}

export function JobReportPDF({ job, results }: JobReportPDFProps) {
  const config = job.config || {};
  const inputFiles = job.input_paths || job.input_files || [];
  const stages = job.stages_to_run || ALL_PIPELINE_STAGES;
  const statusStyle = statusColors[job.status] || statusColors.pending;

  const processingTime = job.started_at
    ? ((job.completed_at ? new Date(job.completed_at) : new Date()).getTime() -
       new Date(job.started_at).getTime()) / 1000
    : null;

  return (
    <Document>
      <Page size="A4" style={styles.page}>
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.title}>{job.name}</Text>
          <Text style={styles.subtitle}>Job ID: {job.id}</Text>
          <View style={[styles.statusBadge, { backgroundColor: statusStyle.bg }]}>
            <Text style={[styles.statusText, { color: statusStyle.text }]}>
              {job.status}
            </Text>
          </View>
        </View>

        {/* Summary Stats */}
        <View style={styles.statsGrid}>
          <View style={styles.statBox}>
            <Text style={styles.statValue}>{job.total_frames || 0}</Text>
            <Text style={styles.statLabel}>Total Frames</Text>
          </View>
          <View style={styles.statBox}>
            <Text style={[styles.statValue, { color: '#16a34a' }]}>
              {job.processed_frames || 0}
            </Text>
            <Text style={styles.statLabel}>Processed</Text>
          </View>
          <View style={styles.statBox}>
            <Text style={[styles.statValue, { color: '#2563eb' }]}>
              {results?.statistics?.total_detections || 0}
            </Text>
            <Text style={styles.statLabel}>Detections</Text>
          </View>
          <View style={styles.statBox}>
            <Text style={[styles.statValue, { color: '#7c3aed' }]}>
              {results?.statistics?.total_tracks || 0}
            </Text>
            <Text style={styles.statLabel}>Tracks</Text>
          </View>
        </View>

        {/* Pipeline Stages */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Pipeline Stages</Text>
          <View style={styles.stagesRow}>
            {ALL_PIPELINE_STAGES.map((stage, idx) => {
              const isSelected = stages.includes(stage);
              const stageNum = STAGE_INFO[stage].number;
              const isCompleted = job.current_stage ? job.current_stage >= stageNum : false;

              return (
                <View key={stage} style={{ flexDirection: 'row', alignItems: 'center' }}>
                  <View style={styles.stageItem}>
                    <View
                      style={[
                        styles.stageCircle,
                        {
                          backgroundColor: !isSelected
                            ? '#cbd5e1'
                            : isCompleted
                            ? '#16a34a'
                            : '#94a3b8',
                        },
                      ]}
                    >
                      <Text style={styles.stageNumber}>{stageNum}</Text>
                    </View>
                    <Text style={styles.stageName}>{STAGE_INFO[stage].name}</Text>
                  </View>
                  {idx < ALL_PIPELINE_STAGES.length - 1 && (
                    <View
                      style={[
                        styles.stageConnector,
                        {
                          backgroundColor:
                            isSelected && stages.includes(ALL_PIPELINE_STAGES[idx + 1])
                              ? isCompleted ? '#16a34a' : '#cbd5e1'
                              : '#e2e8f0',
                        },
                      ]}
                    />
                  )}
                </View>
              );
            })}
          </View>
          {job.progress !== undefined && job.progress > 0 && (
            <View>
              <View style={styles.progressBarContainer}>
                <View style={[styles.progressBar, { width: `${job.progress}%` }]} />
              </View>
              <Text style={styles.progressText}>{job.progress.toFixed(1)}% Complete</Text>
            </View>
          )}
        </View>

        {/* Input Files */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Input Files ({inputFiles.length})</Text>
          <View style={styles.table}>
            {inputFiles.map((file, idx) => (
              <View
                key={idx}
                style={idx === inputFiles.length - 1 ? styles.tableRowLast : styles.fileItem}
              >
                <Text style={styles.fileName}>{file.split('/').pop()}</Text>
                <Text style={styles.filePath}>{file}</Text>
              </View>
            ))}
          </View>
        </View>

        {/* Object Classes */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>
            Object Classes ({(config.object_class_ids || []).length})
          </Text>
          <View style={styles.tagsContainer}>
            {(config.object_class_ids || []).map((cls, idx) => (
              <View key={idx} style={styles.tag}>
                <Text style={styles.tagText}>{cls}</Text>
              </View>
            ))}
          </View>
        </View>

        {/* Detections by Class */}
        {results?.statistics?.detections_by_class &&
         Object.keys(results.statistics.detections_by_class).length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Detections by Class</Text>
            {Object.entries(results.statistics.detections_by_class).map(([cls, count]) => {
              const total = results.statistics.total_detections || 1;
              const percentage = (count / total) * 100;
              return (
                <View key={cls} style={styles.detectionBar}>
                  <View style={styles.detectionLabel}>
                    <Text style={styles.detectionClass}>{cls}</Text>
                    <Text style={styles.detectionCount}>{count} ({percentage.toFixed(1)}%)</Text>
                  </View>
                  <View style={styles.detectionBarBg}>
                    <View style={[styles.detectionBarFill, { width: `${percentage}%` }]} />
                  </View>
                </View>
              );
            })}
          </View>
        )}

        {/* Processing Settings */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Processing Settings</Text>
          <View style={styles.table}>
            <View style={styles.tableRow}>
              <Text style={styles.tableLabel}>Model Variant</Text>
              <Text style={styles.tableValue}>
                {config.sam3_model_variant || 'sam3_hiera_large'}
              </Text>
            </View>
            <View style={styles.tableRow}>
              <Text style={styles.tableLabel}>Confidence Threshold</Text>
              <Text style={styles.tableValue}>{config.sam3_confidence_threshold ?? 0.5}</Text>
            </View>
            <View style={styles.tableRow}>
              <Text style={styles.tableLabel}>IOU Threshold</Text>
              <Text style={styles.tableValue}>{config.sam3_iou_threshold ?? 0.7}</Text>
            </View>
            <View style={styles.tableRow}>
              <Text style={styles.tableLabel}>Batch Size</Text>
              <Text style={styles.tableValue}>{config.sam3_batch_size ?? 4}</Text>
            </View>
            <View style={styles.tableRow}>
              <Text style={styles.tableLabel}>Frame Skip</Text>
              <Text style={styles.tableValue}>{config.frame_skip ?? 1}</Text>
            </View>
            <View style={styles.tableRow}>
              <Text style={styles.tableLabel}>Tracking Enabled</Text>
              <Text style={styles.tableValue}>{config.enable_tracking ? 'Yes' : 'No'}</Text>
            </View>
            <View style={styles.tableRowLast}>
              <Text style={styles.tableLabel}>3D Export Enabled</Text>
              <Text style={styles.tableValue}>{config.export_3d_data ? 'Yes' : 'No'}</Text>
            </View>
          </View>
        </View>

        {/* Timeline */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Timeline</Text>
          <View style={styles.table}>
            <View style={styles.tableRow}>
              <Text style={styles.tableLabel}>Created</Text>
              <Text style={styles.tableValue}>{formatDate(job.created_at)}</Text>
            </View>
            <View style={styles.tableRow}>
              <Text style={styles.tableLabel}>Started</Text>
              <Text style={styles.tableValue}>{formatDate(job.started_at)}</Text>
            </View>
            <View style={styles.tableRow}>
              <Text style={styles.tableLabel}>Completed</Text>
              <Text style={styles.tableValue}>{formatDate(job.completed_at)}</Text>
            </View>
            {processingTime && (
              <View style={styles.tableRowLast}>
                <Text style={styles.tableLabel}>Processing Time</Text>
                <Text style={[styles.tableValue, { color: '#3b82f6', fontFamily: 'Helvetica-Bold' }]}>
                  {formatDuration(processingTime)}
                </Text>
              </View>
            )}
          </View>
        </View>

        {/* Error Message */}
        {job.error_message && (
          <View style={styles.section}>
            <Text style={[styles.sectionTitle, { color: '#dc2626' }]}>Error</Text>
            <View style={styles.errorBox}>
              <Text style={styles.errorText}>{job.error_message}</Text>
            </View>
          </View>
        )}

        {/* Footer */}
        <View style={styles.footer}>
          <Text style={styles.footerText}>Pipeline One</Text>
          <Text style={styles.footerText}>
            Generated: {new Date().toLocaleString()}
          </Text>
        </View>
      </Page>
    </Document>
  );
}
