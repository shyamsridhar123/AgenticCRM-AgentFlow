import { Routes, Route } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Dashboard from './components/Dashboard';
import ChatInterface from './components/ChatInterface';
import LeadsList from './components/LeadsList';
import PipelineView from './components/PipelineView';
import EmailsView from './components/EmailsView';
import MeetingsView from './components/MeetingsView';

function App() {
    return (
        <div className="app-container">
            <Sidebar />
            <main className="main-content">
                <Routes>
                    <Route path="/" element={<Dashboard />} />
                    <Route path="/chat" element={<ChatInterface />} />
                    <Route path="/leads" element={<LeadsList />} />
                    <Route path="/pipeline" element={<PipelineView />} />
                    <Route path="/emails" element={<EmailsView />} />
                    <Route path="/meetings" element={<MeetingsView />} />
                </Routes>
            </main>
        </div>
    );
}

export default App;
