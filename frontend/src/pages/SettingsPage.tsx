export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-secondary-100">Settings</h1>

      {/* SAM 3 Configuration */}
      <div className="card p-6">
        <h2 className="text-lg font-medium text-secondary-100 mb-4">
          SAM 3 Configuration
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="label">Model Variant</label>
            <select className="input">
              <option value="sam3_hiera_tiny">SAM3 Tiny (~400MB, 4GB VRAM)</option>
              <option value="sam3_hiera_small">SAM3 Small (~900MB, 8GB VRAM)</option>
              <option value="sam3_hiera_base">SAM3 Base (~1.8GB, 12GB VRAM)</option>
              <option value="sam3_hiera_large" selected>
                SAM3 Large (~2.4GB, 16GB VRAM)
              </option>
            </select>
          </div>
          <div>
            <label className="label">Precision Mode</label>
            <select className="input">
              <option value="fp32">FP32 (Full Precision)</option>
              <option value="fp16" selected>FP16 (Half Precision)</option>
              <option value="bf16">BF16 (Brain Float)</option>
            </select>
          </div>
          <div>
            <label className="label">Default Confidence Threshold</label>
            <input
              type="range"
              min="0"
              max="100"
              defaultValue="50"
              className="w-full"
            />
            <span className="text-sm text-secondary-400">0.5</span>
          </div>
          <div>
            <label className="label">Default Batch Size</label>
            <input
              type="number"
              defaultValue="8"
              min="1"
              max="32"
              className="input"
            />
          </div>
        </div>
      </div>

      {/* Object Classes */}
      <div className="card p-6">
        <h2 className="text-lg font-medium text-secondary-100 mb-4">
          Object Classes
        </h2>
        <p className="text-secondary-400 mb-4">
          Configure preset and custom object classes for detection.
        </p>
        <div className="space-y-2">
          {['Car', 'Truck', 'Person', 'Cyclist', 'Traffic Sign'].map((cls) => (
            <div
              key={cls}
              className="flex items-center justify-between py-2 px-3 bg-secondary-700 rounded"
            >
              <span className="text-secondary-100">{cls}</span>
              <span className="text-xs text-secondary-400">Preset</span>
            </div>
          ))}
        </div>
        <button className="btn-secondary mt-4">Add Custom Class</button>
      </div>

      {/* Data Paths */}
      <div className="card p-6">
        <h2 className="text-lg font-medium text-secondary-100 mb-4">Data Paths</h2>
        <div className="space-y-4">
          <div>
            <label className="label">SVO2 Directory</label>
            <input
              type="text"
              className="input"
              defaultValue="/home/atlas/dev/pipe1/data/svo2"
              readOnly
            />
          </div>
          <div>
            <label className="label">Output Directory</label>
            <input
              type="text"
              className="input"
              defaultValue="/home/atlas/dev/pipe1/data/output"
              readOnly
            />
          </div>
          <div>
            <label className="label">Models Directory</label>
            <input
              type="text"
              className="input"
              defaultValue="/home/atlas/dev/pipe1/data/models"
              readOnly
            />
          </div>
        </div>
      </div>

      {/* System Info */}
      <div className="card p-6">
        <h2 className="text-lg font-medium text-secondary-100 mb-4">System Info</h2>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-secondary-400">GPU:</span>
            <span className="ml-2 text-secondary-100">NVIDIA GeForce RTX 5090</span>
          </div>
          <div>
            <span className="text-secondary-400">VRAM:</span>
            <span className="ml-2 text-secondary-100">32 GB</span>
          </div>
          <div>
            <span className="text-secondary-400">CUDA Version:</span>
            <span className="ml-2 text-secondary-100">12.6</span>
          </div>
          <div>
            <span className="text-secondary-400">ZED SDK:</span>
            <span className="ml-2 text-secondary-100">5.1</span>
          </div>
        </div>
      </div>
    </div>
  )
}
