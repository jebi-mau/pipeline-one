/**
 * Shalom - Add Object Class Modal component
 */

import { useState } from 'react';
import { Modal } from '../common/Modal';
import { LoadingSpinner } from '../common/LoadingSpinner';
import { useCreateObjectClass } from '../../hooks/useConfig';

interface AddClassModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const KITTI_TYPES = [
  { value: '', label: 'None' },
  { value: 'Car', label: 'Car' },
  { value: 'Van', label: 'Van' },
  { value: 'Truck', label: 'Truck' },
  { value: 'Pedestrian', label: 'Pedestrian' },
  { value: 'Person_sitting', label: 'Person (sitting)' },
  { value: 'Cyclist', label: 'Cyclist' },
  { value: 'Tram', label: 'Tram' },
  { value: 'Misc', label: 'Misc' },
  { value: 'DontCare', label: "Don't Care" },
];

const DEFAULT_COLORS = [
  '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4',
  '#FFEAA7', '#DDA0DD', '#98D8C8', '#F7DC6F',
  '#BB8FCE', '#85C1E9', '#F8B500', '#00CED1',
];

export function AddClassModal({ isOpen, onClose }: AddClassModalProps) {
  const [name, setName] = useState('');
  const [sam3Prompt, setSam3Prompt] = useState('');
  const [color, setColor] = useState(DEFAULT_COLORS[0]);
  const [kittiType, setKittiType] = useState('');

  const createClass = useCreateObjectClass();

  const handleSubmit = async () => {
    if (!name.trim() || !sam3Prompt.trim()) {
      return;
    }

    try {
      await createClass.mutateAsync({
        name: name.trim(),
        prompt: sam3Prompt.trim(),
        color,
        kitti_type: kittiType || undefined,
      });

      // Reset form and close
      setName('');
      setSam3Prompt('');
      setColor(DEFAULT_COLORS[0]);
      setKittiType('');
      onClose();
    } catch (error) {
      console.error('Failed to create object class:', error);
    }
  };

  const canSubmit = name.trim() && sam3Prompt.trim() && !createClass.isPending;

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Add Object Class" size="md">
      <div className="space-y-4">
        {/* Name */}
        <div>
          <label className="block text-sm font-medium text-secondary-300 mb-2">
            Class Name <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g., Person, Vehicle, Tree"
            className="w-full px-3 py-2 bg-secondary-800 border border-secondary-700 rounded-lg text-secondary-100 placeholder-secondary-500 focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
        </div>

        {/* SAM3 Prompt */}
        <div>
          <label className="block text-sm font-medium text-secondary-300 mb-2">
            SAM3 Prompt <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            value={sam3Prompt}
            onChange={(e) => setSam3Prompt(e.target.value)}
            placeholder="Prompt for SAM3 detection..."
            className="w-full px-3 py-2 bg-secondary-800 border border-secondary-700 rounded-lg text-secondary-100 placeholder-secondary-500 focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
          <p className="mt-1 text-xs text-secondary-500">
            Text prompt used by SAM3 to identify this object type
          </p>
        </div>

        {/* Color */}
        <div>
          <label className="block text-sm font-medium text-secondary-300 mb-2">
            Display Color
          </label>
          <div className="flex items-center space-x-4">
            <div className="flex flex-wrap gap-2">
              {DEFAULT_COLORS.map((c) => (
                <button
                  key={c}
                  onClick={() => setColor(c)}
                  className={`w-8 h-8 rounded-full border-2 transition-transform ${
                    color === c ? 'border-white scale-110' : 'border-transparent'
                  }`}
                  style={{ backgroundColor: c }}
                  title={c}
                />
              ))}
            </div>
            <input
              type="color"
              value={color}
              onChange={(e) => setColor(e.target.value)}
              className="w-10 h-10 rounded cursor-pointer border-0"
              title="Custom color"
            />
          </div>
        </div>

        {/* KITTI Type */}
        <div>
          <label className="block text-sm font-medium text-secondary-300 mb-2">
            KITTI Type (optional)
          </label>
          <select
            value={kittiType}
            onChange={(e) => setKittiType(e.target.value)}
            className="w-full px-3 py-2 bg-secondary-800 border border-secondary-700 rounded-lg text-secondary-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            {KITTI_TYPES.map((type) => (
              <option key={type.value} value={type.value}>
                {type.label}
              </option>
            ))}
          </select>
          <p className="mt-1 text-xs text-secondary-500">
            KITTI format object type for dataset export
          </p>
        </div>

        {/* Preview */}
        <div className="p-3 bg-secondary-800 rounded-lg">
          <div className="text-xs text-secondary-500 mb-2">Preview</div>
          <div className="flex items-center space-x-3">
            <div
              className="w-4 h-4 rounded-full"
              style={{ backgroundColor: color }}
            />
            <span className="text-secondary-100 font-medium">{name || 'Class Name'}</span>
            {kittiType && (
              <span className="text-xs text-secondary-500">({kittiType})</span>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="flex justify-end space-x-3 pt-4 border-t border-secondary-700">
          <button
            onClick={onClose}
            className="btn-secondary"
            disabled={createClass.isPending}
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={!canSubmit}
            className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {createClass.isPending ? (
              <span className="flex items-center space-x-2">
                <LoadingSpinner size="sm" />
                <span>Creating...</span>
              </span>
            ) : (
              'Add Class'
            )}
          </button>
        </div>
      </div>
    </Modal>
  );
}
