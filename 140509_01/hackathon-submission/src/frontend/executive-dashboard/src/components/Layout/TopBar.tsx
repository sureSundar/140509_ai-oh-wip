import React from 'react';
import {
  AppBar,
  Toolbar,
  IconButton,
  Typography,
  Button,
  Box,
  Chip
} from '@mui/material';
import {
  Menu as MenuIcon,
  AccountCircle,
  Notifications,
  ExitToApp
} from '@mui/icons-material';
import { useAuth } from '../../context/AuthContext';

interface TopBarProps {
  onMenuClick: () => void;
}

const TopBar: React.FC<TopBarProps> = ({ onMenuClick }) => {
  const { user, logout } = useAuth();

  return (
    <AppBar position="static" elevation={0} sx={{ bgcolor: 'white', color: 'text.primary' }}>
      <Toolbar>
        <IconButton
          color="inherit"
          aria-label="open drawer"
          onClick={onMenuClick}
          edge="start"
          sx={{ mr: 2 }}
        >
          <MenuIcon />
        </IconButton>
        
        <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
          AI-Powered Inventory Optimization
        </Typography>
        
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Chip 
            label="DEMO MODE" 
            color="success" 
            size="small" 
            variant="outlined" 
          />
          
          <IconButton color="inherit">
            <Notifications />
          </IconButton>
          
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <AccountCircle />
            <Typography variant="body2">
              {user?.name || 'Admin User'}
            </Typography>
          </Box>
          
          <Button
            color="inherit"
            startIcon={<ExitToApp />}
            onClick={logout}
            size="small"
          >
            Logout
          </Button>
        </Box>
      </Toolbar>
    </AppBar>
  );
};

export default TopBar;