import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { uploadResume, getLatestResume, getResumeQuestions } from '../services/api';

export default function ResumeUploadPage() {
    const navigate = useNavigate();
    const fileInputRef = useRef(null);

    const [file, setFile] = useState(null);
    const [uploading, setUploading] = useState(false);
    const [analysis, setAnalysis] = useState(null);
    const [questions, setQuestions] = useState([]);
    const [loadingQuestions, setLoadingQuestions] = useState(false);
    const [error, setError] = useState('');
    const [dragOver, setDragOver] = useState(false);

    // Try to load user's latest resume analysis on mount
    useEffect(() => {
        const loadExisting = async () => {
            try {
                const res = await getLatestResume();
                setAnalysis(res.data);
            } catch {
                // No resume uploaded yet — that's fine
            }
        };
        loadExisting();
    }, []);

    const handleFileSelect = (e) => {
        const selected = e.target.files?.[0];
        if (selected && selected.type === 'application/pdf') {
            setFile(selected);
            setError('');
        } else {
            setError('Please select a PDF file.');
        }
    };

    const handleDrop = (e) => {
        e.preventDefault();
        setDragOver(false);
        const dropped = e.dataTransfer.files?.[0];
        if (dropped && dropped.type === 'application/pdf') {
            setFile(dropped);
            setError('');
        } else {
            setError('Please drop a PDF file.');
        }
    };

    const handleUpload = async () => {
        if (!file) return;
        setUploading(true);
        setError('');
        try {
            const res = await uploadResume(file);
            setAnalysis(res.data);
            setFile(null);
            setQuestions([]);
        } catch (err) {
            setError(err.response?.data?.detail || 'Upload failed. Please try again.');
        } finally {
            setUploading(false);
        }
    };

    const handleGenerateQuestions = async () => {
        setLoadingQuestions(true);
        setError('');
        try {
            const res = await getResumeQuestions(5);
            setQuestions(res.data);
        } catch (err) {
            setError(err.response?.data?.detail || 'Failed to generate questions.');
        } finally {
            setLoadingQuestions(false);
        }
    };

    const handleStartInterview = () => {
        // Store resume questions in sessionStorage so InterviewSessionPage can use them
        sessionStorage.setItem('resumeQuestions', JSON.stringify(questions));
        sessionStorage.setItem('resumeCategory', analysis?.predicted_category || 'technical');
        navigate('/interview/resume');
    };

    return (
        <div className="page">
            <div className="page-header">
                <h1 className="page-title">Resume Analyzer</h1>
                <p className="page-subtitle">Upload your resume to get personalized interview questions</p>
            </div>

            {/* Upload Section */}
            <div className="card" style={{ marginBottom: '2rem' }}>
                <div className="card-header">
                    <div className="card-title">📄 Upload Resume</div>
                    <div className="card-subtitle">Supported format: PDF</div>
                </div>

                <div
                    className={`upload-zone ${dragOver ? 'upload-zone--active' : ''}`}
                    onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                    onDragLeave={() => setDragOver(false)}
                    onDrop={handleDrop}
                    onClick={() => fileInputRef.current?.click()}
                    style={{
                        border: `2px dashed ${dragOver ? 'var(--accent-primary)' : 'var(--border-color)'}`,
                        borderRadius: 'var(--radius-md)',
                        padding: '3rem 2rem',
                        textAlign: 'center',
                        cursor: 'pointer',
                        transition: 'var(--transition)',
                        background: dragOver ? 'rgba(129, 140, 248, 0.06)' : 'transparent',
                        marginBottom: '1rem',
                    }}
                >
                    <input
                        ref={fileInputRef}
                        type="file"
                        accept=".pdf"
                        onChange={handleFileSelect}
                        style={{ display: 'none' }}
                    />
                    <div style={{ fontSize: '2.5rem', marginBottom: '0.75rem' }}>
                        {file ? '📎' : '📤'}
                    </div>
                    {file ? (
                        <div>
                            <div style={{ fontWeight: 600 }}>{file.name}</div>
                            <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '0.25rem' }}>
                                {(file.size / 1024).toFixed(1)} KB — Click or drop to replace
                            </div>
                        </div>
                    ) : (
                        <div>
                            <div style={{ fontWeight: 600 }}>Drag & drop your resume here</div>
                            <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: '0.25rem' }}>
                                or click to browse files
                            </div>
                        </div>
                    )}
                </div>

                {error && (
                    <div style={{ color: 'var(--error)', marginBottom: '1rem', fontSize: '0.9rem' }}>
                        ⚠️ {error}
                    </div>
                )}

                <button
                    className="btn btn-primary"
                    onClick={handleUpload}
                    disabled={!file || uploading}
                    style={{ width: '100%' }}
                >
                    {uploading ? 'Analyzing resume...' : 'Upload & Analyze'}
                </button>
            </div>

            {/* Analysis Results */}
            {analysis && (
                <>
                    <div className="card" style={{ marginBottom: '2rem' }}>
                        <div className="card-header">
                            <div className="card-title">🎯 Analysis Results</div>
                            <div className="card-subtitle">
                                From <strong>{analysis.filename}</strong> — uploaded {new Date(analysis.uploaded_at).toLocaleDateString()}
                            </div>
                        </div>

                        {/* Predicted Category */}
                        <div style={{ marginBottom: '1.5rem' }}>
                            <div style={{ fontWeight: 600, marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>
                                Predicted Job Role
                            </div>
                            <div style={{
                                display: 'inline-block',
                                padding: '0.5rem 1.25rem',
                                background: 'var(--accent-gradient)',
                                borderRadius: 'var(--radius-xl)',
                                fontWeight: 700,
                                fontSize: '1.05rem',
                            }}>
                                {analysis.predicted_category}
                            </div>
                        </div>

                        {/* Skills */}
                        <div style={{ marginBottom: '1.5rem' }}>
                            <div style={{ fontWeight: 600, marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>
                                Extracted Skills ({analysis.extracted_skills?.length || 0})
                            </div>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                                {(analysis.extracted_skills || []).map((skill) => (
                                    <span
                                        key={skill}
                                        style={{
                                            padding: '0.35rem 0.85rem',
                                            background: 'var(--bg-glass)',
                                            border: '1px solid var(--border-color)',
                                            borderRadius: 'var(--radius-sm)',
                                            fontSize: '0.85rem',
                                            color: 'var(--accent-primary)',
                                            fontWeight: 500,
                                        }}
                                    >
                                        {skill}
                                    </span>
                                ))}
                                {(!analysis.extracted_skills || analysis.extracted_skills.length === 0) && (
                                    <span style={{ color: 'var(--text-muted)' }}>No skills detected</span>
                                )}
                            </div>
                        </div>

                        {/* Recommended Jobs */}
                        {analysis.recommended_jobs?.length > 0 && (
                            <div>
                                <div style={{ fontWeight: 600, marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>
                                    Recommended Job Roles
                                </div>
                                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                                    {analysis.recommended_jobs.map((job) => (
                                        <span
                                            key={job}
                                            style={{
                                                padding: '0.35rem 0.85rem',
                                                background: 'rgba(52, 211, 153, 0.1)',
                                                border: '1px solid rgba(52, 211, 153, 0.3)',
                                                borderRadius: 'var(--radius-sm)',
                                                fontSize: '0.85rem',
                                                color: 'var(--success)',
                                                fontWeight: 500,
                                            }}
                                        >
                                            {job}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Generate Questions Button */}
                    <div className="card" style={{ marginBottom: '2rem' }}>
                        <div className="card-header">
                            <div className="card-title">💡 Personalized Interview Questions</div>
                            <div className="card-subtitle">AI-generated questions based on your resume skills</div>
                        </div>

                        {questions.length === 0 ? (
                            <button
                                className="btn btn-primary"
                                onClick={handleGenerateQuestions}
                                disabled={loadingQuestions}
                                style={{ width: '100%' }}
                            >
                                {loadingQuestions ? 'Generating questions...' : 'Generate Interview Questions'}
                            </button>
                        ) : (
                            <>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginBottom: '1.5rem' }}>
                                    {questions.map((q, i) => (
                                        <div
                                            key={i}
                                            style={{
                                                padding: '1rem 1.25rem',
                                                background: 'var(--bg-glass)',
                                                border: '1px solid var(--border-color)',
                                                borderRadius: 'var(--radius-md)',
                                            }}
                                        >
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
                                                <span style={{
                                                    fontWeight: 700,
                                                    fontSize: '0.8rem',
                                                    padding: '0.2rem 0.6rem',
                                                    borderRadius: 'var(--radius-sm)',
                                                    background: q.difficulty === 'hard'
                                                        ? 'rgba(248, 113, 113, 0.15)'
                                                        : q.difficulty === 'easy'
                                                            ? 'rgba(52, 211, 153, 0.15)'
                                                            : 'rgba(251, 191, 36, 0.15)',
                                                    color: q.difficulty === 'hard'
                                                        ? 'var(--error)'
                                                        : q.difficulty === 'easy'
                                                            ? 'var(--success)'
                                                            : 'var(--warning)',
                                                }}>
                                                    {q.difficulty?.toUpperCase()}
                                                </span>
                                                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Q{i + 1}</span>
                                            </div>
                                            <div style={{ fontWeight: 500, lineHeight: 1.5 }}>{q.text}</div>
                                            {q.tips && (
                                                <div style={{ marginTop: '0.5rem', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                                                    💡 Tip: {q.tips}
                                                </div>
                                            )}
                                        </div>
                                    ))}
                                </div>

                                <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
                                    <button className="btn btn-primary" onClick={handleStartInterview}>
                                        🎙️ Start Resume-Based Interview
                                    </button>
                                    <button className="btn btn-secondary" onClick={handleGenerateQuestions} disabled={loadingQuestions}>
                                        {loadingQuestions ? 'Regenerating...' : '🔄 Regenerate Questions'}
                                    </button>
                                </div>
                            </>
                        )}
                    </div>
                </>
            )}
        </div>
    );
}
