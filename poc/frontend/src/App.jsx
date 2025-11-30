import React, { useState, useCallback } from 'react';
import './App.css';

// --- Firebase Initialization (Mandatory for the environment) ---

// Global variables provided by the environment
// const firebaseConfig = typeof __firebase_config !== 'undefined' ? JSON.parse(__firebase_config) : {};
// const initialAuthToken = typeof __initial_auth_token !== 'undefined' ? __initial_auth_token : null;

// // Initialize Firebase services
// const app = Object.keys(firebaseConfig).length > 0 ? initializeApp(firebaseConfig) : null;
// const auth = app ? getAuth(app) : null;
// const db = app ? getFirestore(app) : null;


// --- Component Definitions ---

const TaskCard = React.memo(({ task }) => (
    <div className="task-card">
        {/* Card Header */}
        <div className="card-header">
             <h3 className="card-title">
                {task.title || <span className="loading-text">Generating Task...</span>}
            </h3>
            <div className={`status-badge ${task.status === 'completed' ? 'completed' : 'active'}`}>
                <span className={`status-dot ${task.status === 'completed' ? 'completed' : 'active'}`}></span>
                <span>{task.status === 'completed' ? 'Done' : 'Active'}</span>
            </div>
        </div>

        {/* Card Body */}
        <div className="card-body">
            <div className="card-description">
                {task.description ? (
                    <p>{task.description}</p>
                ) : (
                    <div className="skeleton-container">
                        <div className="skeleton-line"></div>
                        <div className="skeleton-line short"></div>
                        <div className="skeleton-line shorter"></div>
                    </div>
                )}
            </div>
        </div>
        
        {/* Card Footer */}
        {task.tags && task.tags.length > 0 && (
            <div className="card-footer">
                <div className="tags-container">
                    {task.tags.map((tag, index) => (
                        <span key={index} className="tag">
                            #{tag}
                        </span>
                    ))}
                </div>
            </div>
        )}
    </div>
));


const App = () => {
    const [projectPrompt, setProjectPrompt] = useState('Build a streaming task manager app using FastAPI and React.');
    const [tasks, setTasks] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);


    // 2. Stream Handling Function (EventSource for Streaming)
    const handleStream = useCallback(() => {

        setIsLoading(true);
        setTasks([]);
        setError(null);

        // Encode the prompt as a query parameter
        const backendUrl = `http://127.0.0.1:8000/api/stream_tasks?prompt=${encodeURIComponent(projectPrompt)}`;
        
        // Initialize EventSource
        const eventSource = new EventSource(backendUrl);

        eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);

                if (data.status === 'completed') {
                    console.log("Stream completed.");
                    setIsLoading(false);
                    eventSource.close();
                    
                    // Final update to mark last task as completed
                    setTasks(prevTasks => {
                        if (prevTasks.length > 0) {
                            const lastTask = prevTasks[prevTasks.length - 1];
                            if (lastTask.status !== 'completed') {
                                prevTasks[prevTasks.length - 1] = { ...lastTask, status: 'completed' };
                            }
                        }
                        return [...prevTasks];
                    });

                } else if (data.status === 'error') {
                    setError(`Backend Error: ${data.detail}`);
                    setIsLoading(false);
                    eventSource.close();
                } else if (data.id) {
                    // Handle Task Updates (Upsert logic)
                    setTasks(prevTasks => {
                        const existingTaskIndex = prevTasks.findIndex(t => t.id === data.id);
                        
                        if (existingTaskIndex !== -1) {
                            // Update existing task
                            const updatedTasks = [...prevTasks];
                            updatedTasks[existingTaskIndex] = { ...updatedTasks[existingTaskIndex], ...data };
                            return updatedTasks;
                        } else {
                            // Add new task
                            // First, mark the previous task as completed (if any)
                            const updatedTasks = [...prevTasks];
                            if (updatedTasks.length > 0) {
                                const lastTask = updatedTasks[updatedTasks.length - 1];
                                if (lastTask.status !== 'completed') {
                                    updatedTasks[updatedTasks.length - 1] = { ...lastTask, status: 'completed' };
                                }
                            }
                            return [...updatedTasks, { ...data, status: 'streaming' }];
                        }
                    });
                }
            } catch (e) {
                console.error("Error parsing SSE data:", event.data, e);
            }
        };

        eventSource.onerror = (e) => {
            console.error("EventSource failed:", e);
            // EventSource often retries automatically, but for this generation we want to stop on hard error
            // Check readyState: 0=CONNECTING, 1=OPEN, 2=CLOSED
            if (eventSource.readyState === EventSource.CLOSED) {
                 setError("Connection closed.");
                 setIsLoading(false);
            } else {
                // If it's a network error or server down, we might want to close
                // But typically we can just let it try or close it manually
                // For this demo, let's close on error
                eventSource.close();
                setError("Stream connection failed.");
                setIsLoading(false);
            }
        };

        // Cleanup function if component unmounts or re-runs
        return () => {
            eventSource.close();
        };

    }, [projectPrompt]);

    return (
        <div className="app-container">
            {/* Main Content Area */}
            <div>
                
                {/* Minimal Header */}
                <header className="app-header">
                    <div className="agent-badge">
                        <span className="ping-wrapper">
                          <span className="ping-animate"></span>
                          <span className="ping-dot"></span>
                        </span>
                        <span>Agent Active</span>
                    </div>
                    <h1 className="app-title">
                        Idea to <span>Plan</span>
                    </h1>
                    <p className="app-subtitle">
                        Watch as your project is broken down into actionable tasks in real-time.
                    </p>
                </header>

                {/* Error Banner */}
                {error && (
                    <div className="error-banner" role="alert">
                        <div className="flex">
                            <div className="flex-shrink-0">⚠️</div>
                            <div className="error-content">
                                <p className="error-text">{error}</p>
                            </div>
                        </div>
                    </div>
                )}

                {/* Task Grid */}
                <div className="task-grid">
                    {tasks.length > 0 ? (
                        <>
                            {tasks.map((task) => (
                                <TaskCard key={task.id} task={task} />
                            ))}
                        </>
                    ) : (
                        <div className="empty-state">
                            <div className="empty-circle"></div>
                            <p className="empty-text">Waiting for your brilliant idea...</p>
                        </div>
                    )}
                </div>
            </div>

            {/* Sticky Bottom Input Area */}
            <div className="input-area-wrapper">
                <div className="input-container">
                    <div className="input-box">
                        <div className="relative flex items-end" style={{ width: '100%' }}>
                            <textarea
                                id="prompt"
                                rows="1"
                                className="prompt-textarea"
                                value={projectPrompt}
                                onChange={(e) => {
                                    setProjectPrompt(e.target.value);
                                    e.target.style.height = 'auto';
                                    e.target.style.height = e.target.scrollHeight + 'px';
                                }}
                                placeholder="Describe your dream app..."
                                disabled={isLoading}
                                style={{ height: '60px' }}
                            />
                            <button
                                onClick={handleStream}
                                disabled={isLoading || !projectPrompt.trim()}
                                className="generate-btn"
                            >
                                {isLoading ? (
                                    <div className="loading-spinner-container">
                                        <svg className="spinner" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                            <path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                        </svg>
                                    </div>
                                ) : 'Generate →'}
                            </button>
                        </div>
                    </div>
                    <div className="powered-by">
                        <p>Powered by LangGraph • FastAPI • React • Streaming</p>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default App;
