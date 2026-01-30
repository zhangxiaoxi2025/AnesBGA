import { useState } from 'react'
import './App.css'

// API基础URL - Vercel 部署时使用相对路径
const API_BASE_URL = import.meta.env.PROD ? '' : 'http://localhost:8000'

function App() {
  const [step, setStep] = useState<'upload' | 'review' | 'input' | 'result'>('upload')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string>('')
  const [ocrResult, setOcrResult] = useState<any>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string>('')

  // 生命体征数据
  const [vitalSigns, setVitalSigns] = useState({
    blood_pressure_systolic: '',
    blood_pressure_diastolic: '',
    heart_rate: '',
    temperature: '',
    spo2: '',
    respiratory_rate: ''
  })

  // 麻醉参数
  const [anesthesia, setAnesthesia] = useState({
    anesthesia_type: '',
    intubated: '',
    medications: '',
    notes: ''
  })

  // AI分析结果
  const [analysisResult, setAnalysisResult] = useState<any>(null)

  // 患者体重
  const [weight, setWeight] = useState<string>('')

  // 处理文件选择
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      setSelectedFile(file)
      setPreviewUrl(URL.createObjectURL(file))
      setStep('review')
      setError('')
    }
  }

  // OCR识别
  const handleOCR = async () => {
    if (!selectedFile) return

    setIsLoading(true)
    setError('')

    const formData = new FormData()
    formData.append('file', selectedFile)
    if (weight) {
      formData.append('weight', weight)
    }

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/ocr`, {
        method: 'POST',
        body: formData
      })

      const data = await response.json()

      if (data.success) {
        setOcrResult(data.ocr_result)
        setStep('input')
      } else {
        setError(data.error || 'OCR识别失败')
      }
    } catch (err: any) {
      setError('网络错误：' + err.message)
    } finally {
      setIsLoading(false)
    }
  }

  // AI分析
  const handleAnalyze = async () => {
    if (!ocrResult) return

    setIsLoading(true)
    setError('')

    const formData = new FormData()
    formData.append('blood_gas_json', JSON.stringify(ocrResult))

    // 添加体重
    if (weight) {
      formData.append('weight', weight)
    }

    // 只添加有值的生命体征
    const validVitalSigns: any = {}
    Object.entries(vitalSigns).forEach(([key, value]) => {
      if (value) validVitalSigns[key] = parseFloat(value as string) || value
    })
    if (Object.keys(validVitalSigns).length > 0) {
      formData.append('vital_signs_json', JSON.stringify(validVitalSigns))
    }

    // 只添加有值的麻醉参数
    const validAnesthesia: any = {}
    Object.entries(anesthesia).forEach(([key, value]) => {
      if (value) validAnesthesia[key] = value
    })
    if (Object.keys(validAnesthesia).length > 0) {
      formData.append('anesthesia_json', JSON.stringify(validAnesthesia))
    }

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/analyze`, {
        method: 'POST',
        body: formData
      })

      const data = await response.json()
      setAnalysisResult(data)
      setStep('result')
    } catch (err: any) {
      setError('分析失败：' + err.message)
    } finally {
      setIsLoading(false)
    }
  }

  // 重新开始
  const handleReset = () => {
    setStep('upload')
    setSelectedFile(null)
    setPreviewUrl('')
    setOcrResult(null)
    setWeight('')
    setVitalSigns({
      blood_pressure_systolic: '',
      blood_pressure_diastolic: '',
      heart_rate: '',
      temperature: '',
      spo2: '',
      respiratory_rate: ''
    })
    setAnesthesia({
      anesthesia_type: '',
      intubated: '',
      medications: '',
      notes: ''
    })
    setAnalysisResult(null)
    setError('')
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-3 sm:p-4">
      <div className="max-w-4xl mx-auto">
        {/* 头部 */}
        <div className="text-center py-4 sm:py-6">
          <h1 className="text-2xl sm:text-3xl md:text-4xl font-bold text-gray-800 mb-1 sm:mb-2">🩺 血气分析助手</h1>
          <p className="text-sm sm:text-base text-gray-600">AI驱动的围术期血气分析辅助决策</p>
        </div>

        {/* 错误提示 */}
        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
            <p className="font-bold">错误</p>
            <p>{error}</p>
          </div>
        )}

        {/* 加载中 */}
        {isLoading && (
          <div className="bg-blue-100 border border-blue-400 text-blue-700 px-4 py-3 rounded mb-4 text-center">
            <p>⏳ 处理中，请稍候...</p>
          </div>
        )}

        {/* 步骤1：上传图片 */}
        {step === 'upload' && (
          <div className="bg-white rounded-lg shadow-lg p-4 sm:p-6">
            <h2 className="text-xl sm:text-2xl font-bold mb-4 text-gray-800">📸 上传血气报告</h2>
            <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 sm:p-8 text-center hover:border-blue-500 transition touch-manipulation">
              <input
                type="file"
                accept="image/jpeg,image/jpg,image/png"
                capture="environment"
                onChange={handleFileSelect}
                className="hidden"
                id="file-upload"
              />
              <label htmlFor="file-upload" className="cursor-pointer block">
                <div className="text-5xl sm:text-6xl mb-3">📷</div>
                <p className="text-lg sm:text-xl text-gray-700 mb-1">点击上传或拍照</p>
                <p className="text-xs sm:text-sm text-gray-500">支持 JPG、PNG 格式</p>
              </label>
            </div>
          </div>
        )}

        {/* 步骤2：预览并识别 */}
        {step === 'review' && previewUrl && (
          <div className="bg-white rounded-lg shadow-lg p-4 sm:p-6">
            <h2 className="text-xl sm:text-2xl font-bold mb-4 text-gray-800">👀 确认图片</h2>
            <img src={previewUrl} alt="Preview" className="w-full max-h-64 sm:max-h-80 object-contain mb-4 rounded" />

            {/* 患者体重输入 */}
            <div className="mb-4">
              <label className="block text-gray-700 font-semibold mb-2">
                患者体重 (kg)
              </label>
              <input
                type="number"
                placeholder="输入患者体重"
                value={weight}
                onChange={(e) => setWeight(e.target.value)}
                className="w-full border border-gray-300 rounded px-4 py-3 text-lg"
                inputMode="decimal"
              />
              <p className="text-xs sm:text-sm text-gray-500 mt-1">
                用于计算酸碱纠正药量，建议填写
              </p>
            </div>

            <div className="flex flex-col sm:flex-row gap-3">
              <button
                onClick={handleOCR}
                disabled={isLoading}
                className="flex-1 bg-blue-600 text-white py-4 px-6 rounded-lg font-bold text-lg hover:bg-blue-700 disabled:bg-gray-400 transition touch-manipulation"
              >
                ✓ 开始识别
              </button>
              <button
                onClick={() => setStep('upload')}
                className="px-6 py-4 border border-gray-300 rounded-lg hover:bg-gray-100 transition touch-manipulation"
              >
                重新选择
              </button>
            </div>
          </div>
        )}

        {/* 步骤3：补充数据 */}
        {step === 'input' && ocrResult && (
          <div className="space-y-4 sm:space-y-6">
            {/* OCR识别结果 */}
            <div className="bg-white rounded-lg shadow-lg p-4 sm:p-6">
              <h2 className="text-xl sm:text-2xl font-bold mb-4 text-gray-800">🔍 识别结果</h2>
              {/* 核心指标 */}
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2 sm:gap-3 mb-4">
                {ocrResult.ph && (
                  <div className="bg-blue-50 rounded-lg p-3 text-center">
                    <p className="text-xs sm:text-sm text-gray-600">pH</p>
                    <p className="text-xl sm:text-2xl font-bold text-blue-600">{ocrResult.ph}</p>
                  </div>
                )}
                {ocrResult.po2 && (
                  <div className="bg-green-50 rounded-lg p-3 text-center">
                    <p className="text-xs sm:text-sm text-gray-600">PO2</p>
                    <p className="text-xl sm:text-2xl font-bold text-green-600">{ocrResult.po2}</p>
                    <p className="text-xs text-gray-500">mmHg</p>
                  </div>
                )}
                {ocrResult.pco2 && (
                  <div className="bg-yellow-50 rounded-lg p-3 text-center">
                    <p className="text-xs sm:text-sm text-gray-600">PCO2</p>
                    <p className="text-xl sm:text-2xl font-bold text-yellow-600">{ocrResult.pco2}</p>
                    <p className="text-xs text-gray-500">mmHg</p>
                  </div>
                )}
                {ocrResult.be_ecf !== null && ocrResult.be_ecf !== undefined && (
                  <div className="bg-red-50 rounded-lg p-3 text-center">
                    <p className="text-xs sm:text-sm text-gray-600">BE</p>
                    <p className="text-xl sm:text-2xl font-bold text-red-600">{ocrResult.be_ecf}</p>
                    <p className="text-xs text-gray-500">mmol/L</p>
                  </div>
                )}
              </div>
              {/* 其他指标 - 简化显示 */}
              <div className="text-xs sm:text-sm text-gray-600">
                <p className="mb-2">
                  {ocrResult.na && `Na+: ${ocrResult.na} | `}
                  {ocrResult.k && `K+: ${ocrResult.k} | `}
                  {ocrResult.ca && `Ca++: ${ocrResult.ca}`}
                </p>
                <p className="mb-2">
                  {ocrResult.hco3_act && `HCO3-: ${ocrResult.hco3_act} | `}
                  {ocrResult.lac && `LAC: ${ocrResult.lac}`}
                </p>
                {ocrResult.thbc && <p>THbc: {ocrResult.thbc} g/L</p>}
              </div>
              {ocrResult.confidence !== undefined && (
                <p className="text-xs sm:text-sm text-gray-500 mt-3">识别置信度: {(ocrResult.confidence * 100).toFixed(0)}%</p>
              )}
              {ocrResult.missing_fields && ocrResult.missing_fields.length > 0 && (
                <p className="text-xs sm:text-sm text-orange-600 mt-2">未识别: {ocrResult.missing_fields.join(", ")}</p>
              )}
            </div>

            {/* 生命体征（可选） */}
            <div className="bg-white rounded-lg shadow-lg p-4 sm:p-6">
              <h3 className="text-lg sm:text-xl font-bold mb-4 text-gray-800">💓 生命体征（可选）</h3>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                <input
                  type="number"
                  placeholder="收缩压"
                  value={vitalSigns.blood_pressure_systolic}
                  onChange={(e) => setVitalSigns({...vitalSigns, blood_pressure_systolic: e.target.value})}
                  className="border border-gray-300 rounded px-3 py-3 text-base"
                  inputMode="numeric"
                />
                <input
                  type="number"
                  placeholder="舒张压"
                  value={vitalSigns.blood_pressure_diastolic}
                  onChange={(e) => setVitalSigns({...vitalSigns, blood_pressure_diastolic: e.target.value})}
                  className="border border-gray-300 rounded px-3 py-3 text-base"
                  inputMode="numeric"
                />
                <input
                  type="number"
                  placeholder="心率"
                  value={vitalSigns.heart_rate}
                  onChange={(e) => setVitalSigns({...vitalSigns, heart_rate: e.target.value})}
                  className="border border-gray-300 rounded px-3 py-3 text-base"
                  inputMode="numeric"
                />
                <input
                  type="number"
                  step="0.1"
                  placeholder="体温"
                  value={vitalSigns.temperature}
                  onChange={(e) => setVitalSigns({...vitalSigns, temperature: e.target.value})}
                  className="border border-gray-300 rounded px-3 py-3 text-base"
                  inputMode="decimal"
                />
                <input
                  type="number"
                  placeholder="SpO2"
                  value={vitalSigns.spo2}
                  onChange={(e) => setVitalSigns({...vitalSigns, spo2: e.target.value})}
                  className="border border-gray-300 rounded px-3 py-3 text-base"
                  inputMode="numeric"
                />
                <input
                  type="number"
                  placeholder="呼吸"
                  value={vitalSigns.respiratory_rate}
                  onChange={(e) => setVitalSigns({...vitalSigns, respiratory_rate: e.target.value})}
                  className="border border-gray-300 rounded px-3 py-3 text-base"
                  inputMode="numeric"
                />
              </div>
            </div>

            {/* 麻醉参数（可选） */}
            <div className="bg-white rounded-lg shadow-lg p-4 sm:p-6">
              <h3 className="text-lg sm:text-xl font-bold mb-4 text-gray-800">💉 麻醉参数（可选）</h3>
              <div className="space-y-3">
                <select
                  value={anesthesia.anesthesia_type}
                  onChange={(e) => setAnesthesia({...anesthesia, anesthesia_type: e.target.value})}
                  className="w-full border border-gray-300 rounded px-3 py-3 text-base"
                >
                  <option value="">麻醉方式</option>
                  <option value="全身麻醉">全身麻醉</option>
                  <option value="椎管内麻醉">椎管内麻醉</option>
                  <option value="神经阻滞">神经阻滞</option>
                  <option value="局部麻醉">局部麻醉</option>
                </select>
                <div className="flex gap-2">
                  <select
                    value={anesthesia.intubated}
                    onChange={(e) => setAnesthesia({...anesthesia, intubated: e.target.value})}
                    className="flex-1 border border-gray-300 rounded px-3 py-3 text-base"
                  >
                    <option value="">气管插管</option>
                    <option value="是">是</option>
                    <option value="否">否</option>
                  </select>
                  <input
                    type="text"
                    placeholder="用药"
                    value={anesthesia.medications}
                    onChange={(e) => setAnesthesia({...anesthesia, medications: e.target.value})}
                    className="flex-1 border border-gray-300 rounded px-3 py-3 text-base"
                  />
                </div>
              </div>
            </div>

            {/* 操作按钮 */}
            <div className="flex flex-col gap-3">
              <button
                onClick={handleAnalyze}
                disabled={isLoading}
                className="w-full bg-green-600 text-white py-4 px-6 rounded-lg font-bold text-lg hover:bg-green-700 disabled:bg-gray-400 transition touch-manipulation"
              >
                🤖 开始AI分析
              </button>
              <button
                onClick={handleReset}
                className="w-full py-3 px-6 border border-gray-300 rounded-lg hover:bg-gray-100 transition touch-manipulation"
              >
                🔄 重新开始
              </button>
            </div>
          </div>
        )}

        {/* 步骤4：分析结果 */}
        {step === 'result' && analysisResult && (
          <div className="space-y-4 sm:space-y-6">
            {/* 总体评估 */}
            <div className="bg-white rounded-lg shadow-lg p-4 sm:p-6">
              <h2 className="text-xl sm:text-2xl font-bold mb-4 text-gray-800">📊 分析结果</h2>
              {/* 检查 assessment 是否存在且有内容 */}
              {analysisResult.assessment && Object.keys(analysisResult.assessment).length > 0 ? (
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-4">
                  <div className="bg-blue-50 p-3 rounded">
                    <p className="text-xs sm:text-sm text-gray-600">酸碱状态</p>
                    <p className="text-lg font-bold">{analysisResult.assessment.acid_base_status || '未评估'}</p>
                  </div>
                  <div className="bg-green-50 p-3 rounded">
                    <p className="text-xs sm:text-sm text-gray-600">氧合状态</p>
                    <p className="text-lg font-bold">{analysisResult.assessment.oxygenation || '未评估'}</p>
                  </div>
                  <div className={`p-3 rounded ${
                    analysisResult.assessment.risk_level === '高风险' ? 'bg-red-100' :
                    analysisResult.assessment.risk_level === '中风险' ? 'bg-yellow-100' :
                    'bg-green-100'
                  }`}>
                    <p className="text-xs sm:text-sm text-gray-600">风险等级</p>
                    <p className="text-lg font-bold">{analysisResult.assessment.risk_level || '未知'}</p>
                  </div>
                </div>
              ) : (
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-4">
                  <p className="text-yellow-800 font-semibold">⚠️ AI 返回的分析数据不完整</p>
                  <p className="text-sm text-yellow-700 mt-1">可能原因：血气数据缺失、AI 分析超时或返回格式错误</p>
                </div>
              )}
              {analysisResult.assessment?.clinical_summary && (
                <p className="text-gray-700 mt-3 p-3 bg-gray-50 rounded text-sm sm:text-base">{analysisResult.assessment.clinical_summary}</p>
              )}
            </div>

            {/* 酸中毒纠正 */}
            {analysisResult.acid_correction && analysisResult.acid_correction.condition && (
              <div className="bg-white rounded-lg shadow-lg p-4 sm:p-6">
                <h3 className="text-lg sm:text-xl font-bold mb-4 text-gray-800">🧪 酸中毒纠正</h3>
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                  <p className="font-semibold text-red-800 mb-2">{analysisResult.acid_correction.condition}</p>
                  {analysisResult.acid_correction.calculated_na_hco3_mmol !== null && (
                    <>
                      <p className="text-sm text-gray-700">公式: {analysisResult.acid_correction.formula_used}</p>
                      <p className="text-sm text-gray-700">依据: {analysisResult.acid_correction.calculation_basis}</p>
                      <div className="mt-3 p-3 bg-white rounded border border-red-300">
                        <p className="text-lg font-bold text-red-700">
                          💉 碳酸氢钠: {analysisResult.acid_correction.nahco3_5_percent_ml} ml
                        </p>
                        <p className="text-xs sm:text-sm text-gray-600 mt-1">({analysisResult.acid_correction.calculated_na_hco3_mmol} mmol)</p>
                        <p className="text-sm text-orange-600 mt-2">⚠️ {analysisResult.acid_correction.recommendation}</p>
                      </div>
                    </>
                  )}
                </div>
              </div>
            )}

            {/* 碱中毒管理 */}
            {analysisResult.alkalosis_management && analysisResult.alkalosis_management.condition && (
              <div className="bg-white rounded-lg shadow-lg p-4 sm:p-6">
                <h3 className="text-lg sm:text-xl font-bold mb-4 text-gray-800">🧪 碱中毒管理</h3>
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <p className="font-semibold text-blue-800 mb-2">{analysisResult.alkalosis_management.condition}</p>
                  <p className="text-gray-700">类型: {analysisResult.alkalosis_management.type}</p>
                  {analysisResult.alkalosis_management.fluid_therapy && (
                    <p className="text-gray-700 mt-2">💧 补液: {analysisResult.alkalosis_management.fluid_therapy}</p>
                  )}
                  {analysisResult.alkalosis_management.ventilation_adjustment && (
                    <p className="text-gray-700 mt-2">💨 呼吸: {analysisResult.alkalosis_management.ventilation_adjustment}</p>
                  )}
                </div>
              </div>
            )}

            {/* 输血指导 */}
            {analysisResult.transfusion_guidance && analysisResult.transfusion_guidance.condition && (
              <div className="bg-white rounded-lg shadow-lg p-4 sm:p-6">
                <h3 className="text-lg sm:text-xl font-bold mb-4 text-gray-800">🩸 输血指导</h3>
                <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
                  <p className="font-semibold text-purple-800 mb-2">{analysisResult.transfusion_guidance.condition}</p>
                  <div className="grid grid-cols-2 gap-3 mt-2">
                    <div>
                      <p className="text-xs sm:text-sm text-gray-600">当前 THbc</p>
                      <p className="text-lg font-bold">{analysisResult.transfusion_guidance.current_thbc} g/L</p>
                    </div>
                    <div>
                      <p className="text-xs sm:text-sm text-gray-600">目标 THbc</p>
                      <p className="text-lg font-bold">{analysisResult.transfusion_guidance.target_thbc} g/L</p>
                    </div>
                  </div>
                  <div className="mt-3 p-3 bg-white rounded border border-purple-300">
                    <p className="text-lg font-bold text-purple-700">
                      🩸 红细胞: {analysisResult.transfusion_guidance.prbc_units_estimated} U
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* 电解质纠正 */}
            {analysisResult.electrolyte_correction && (
              <div className="bg-white rounded-lg shadow-lg p-4 sm:p-6">
                <h3 className="text-lg sm:text-xl font-bold mb-4 text-gray-800">⚡ 电解质纠正</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {/* 钾 */}
                  {analysisResult.electrolyte_correction.potassium && (
                    <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                      <h4 className="font-semibold text-yellow-800 mb-1">钾 (K+)</h4>
                      <p className="text-gray-700 text-sm">{analysisResult.electrolyte_correction.potassium.current_k} mmol/L</p>
                      {analysisResult.electrolyte_correction.potassium.kcl_recommendation && (
                        <p className="mt-1 text-orange-700 font-medium text-sm">
                          💊 {analysisResult.electrolyte_correction.potassium.kcl_recommendation}
                        </p>
                      )}
                    </div>
                  )}
                  {/* 钙 */}
                  {analysisResult.electrolyte_correction.calcium && (
                    <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                      <h4 className="font-semibold text-green-800 mb-1">钙 (Ca++)</h4>
                      <p className="text-gray-700 text-sm">{analysisResult.electrolyte_correction.calcium.current_ca} mmol/L</p>
                      {analysisResult.electrolyte_correction.calcium.calcium_recommendation && (
                        <p className="mt-1 text-green-700 font-medium text-sm">
                          💊 {analysisResult.electrolyte_correction.calcium.calcium_recommendation}
                        </p>
                      )}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* 临床发现 */}
            {analysisResult.findings && analysisResult.findings.length > 0 && (
              <div className="bg-white rounded-lg shadow-lg p-4 sm:p-6">
                <h3 className="text-lg sm:text-xl font-bold mb-4 text-gray-800">🔍 临床发现</h3>
                <div className="space-y-3">
                  {analysisResult.findings.map((finding: any, index: number) => (
                    <div key={index} className="border-l-4 border-blue-500 pl-3 py-2">
                      <p className="font-semibold text-sm">{finding.category} - {finding.parameter}</p>
                      <p className="text-gray-700 text-sm">{finding.value} ({finding.reference})</p>
                      <p className="text-xs text-gray-600">{finding.interpretation}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 处理建议 */}
            {analysisResult.recommendations && analysisResult.recommendations.length > 0 && (
              <div className="bg-white rounded-lg shadow-lg p-4 sm:p-6">
                <h3 className="text-lg sm:text-xl font-bold mb-4 text-gray-800">💡 处理建议</h3>
                <div className="space-y-3">
                  {analysisResult.recommendations.map((rec: any, index: number) => (
                    <div key={index} className={`p-3 rounded border-l-4 ${
                      rec.priority === '高' ? 'border-red-500 bg-red-50' :
                      rec.priority === '中' ? 'border-yellow-500 bg-yellow-50' :
                      'border-green-500 bg-green-50'
                    }`}>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-bold text-sm">{rec.action}</span>
                        <span className={`text-xs px-2 py-0.5 rounded ${
                          rec.priority === '高' ? 'bg-red-200' :
                          rec.priority === '中' ? 'bg-yellow-200' :
                          'bg-green-200'
                        }`}>
                          {rec.priority === '高' ? '高' : rec.priority === '中' ? '中' : '低'}
                        </span>
                      </div>
                      <p className="text-gray-700 text-sm">{rec.detail}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 警告 */}
            {analysisResult.alerts && analysisResult.alerts.length > 0 && (
              <div className="bg-red-50 border border-red-300 rounded-lg p-4">
                <h3 className="text-lg sm:text-xl font-bold mb-3 text-red-800">⚠️ 重要警告</h3>
                <div className="space-y-2">
                  {analysisResult.alerts.map((alert: any, index: number) => (
                    <div key={index} className="border-l-4 border-red-500 pl-3 py-2 bg-red-100 rounded">
                      <p className="font-semibold text-red-800 text-sm">{alert.message}</p>
                      {alert.recommendation && (
                        <p className="text-xs text-red-700 mt-1">建议: {alert.recommendation}</p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 安全警示 */}
            {analysisResult.safety_warning && (
              <div className="bg-orange-50 border border-orange-300 rounded-lg p-3">
                <p className="text-orange-800 font-semibold text-sm">⚠️ {analysisResult.safety_warning}</p>
              </div>
            )}

            {/* 免责声明 */}
            <div className="bg-gray-100 rounded-lg p-3 text-xs text-gray-600 italic">
              <p>{analysisResult.disclaimer || '以上分析基于AI算法，仅供临床参考。具体治疗方案必须由具有执业资格的主治医生根据患者整体情况决定。本系统不承担任何医疗责任。'}</p>
            </div>

            {/* 操作按钮 */}
            <button
              onClick={handleReset}
              className="w-full bg-blue-600 text-white py-4 px-6 rounded-lg font-bold text-lg hover:bg-blue-700 transition touch-manipulation"
            >
              🔄 分析新报告
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

export default App
