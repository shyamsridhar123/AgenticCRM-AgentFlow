import { NavLink } from 'react-router-dom';
import {
    LayoutDashboard,
    MessageSquare,
    Users,
    TrendingUp,
    Mail,
    Calendar,
    Settings,
    Sparkles
} from 'lucide-react';

function Sidebar() {
    return (
        <aside className="sidebar">
            {/* Logo */}
            <div className="logo">
                <div className="logo-icon">
                    <Sparkles size={24} color="white" />
                </div>
                <span className="logo-text">Agentic CRM</span>
            </div>

            {/* Main Navigation */}
            <nav className="nav-section">
                <span className="nav-section-title">Main</span>
                <NavLink to="/" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
                    <LayoutDashboard size={18} />
                    Dashboard
                </NavLink>
                <NavLink to="/chat" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
                    <MessageSquare size={18} />
                    AI Chat
                </NavLink>
            </nav>

            {/* CRM Navigation */}
            <nav className="nav-section">
                <span className="nav-section-title">CRM</span>
                <NavLink to="/leads" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
                    <Users size={18} />
                    Leads
                </NavLink>
                <NavLink to="/pipeline" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
                    <TrendingUp size={18} />
                    Pipeline
                </NavLink>
                <NavLink to="/emails" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
                    <Mail size={18} />
                    Emails
                </NavLink>
                <NavLink to="/meetings" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
                    <Calendar size={18} />
                    Meetings
                </NavLink>
            </nav>

            {/* Settings */}
            <nav className="nav-section" style={{ marginTop: 'auto' }}>
                <NavLink to="/settings" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
                    <Settings size={18} />
                    Settings
                </NavLink>
            </nav>
        </aside>
    );
}

export default Sidebar;
