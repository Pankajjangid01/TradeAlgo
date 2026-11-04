import { createTheme, ThemeOptions } from '@mui/material/styles';

const themeOptions: ThemeOptions = {
  palette: {
    mode: 'dark',
    primary: {
      main: '#00d4aa',
      light: '#4dffe0',
      dark: '#00a17c',
      contrastText: '#000',
    },
    secondary: {
      main: '#ff6b6b',
      light: '#ff9e9e',
      dark: '#c63c3c',
      contrastText: '#fff',
    },
    background: {
      default: '#0d1117',
      paper: '#161b22',
    },
    text: {
      primary: '#e6edf3',
      secondary: '#8b949e',
    },
    success: {
      main: '#3fb950',
      light: '#56d364',
      dark: '#2ea043',
    },
    error: {
      main: '#f85149',
      light: '#ff7b72',
      dark: '#da3633',
    },
    warning: {
      main: '#d29922',
      light: '#e3b341',
      dark: '#9e6a03',
    },
    info: {
      main: '#58a6ff',
      light: '#79c0ff',
      dark: '#388bfd',
    },
    divider: '#30363d',
  },
  typography: {
    fontFamily: '"JetBrains Mono", "Fira Code", "Consolas", monospace',
    h1: { fontSize: '2.5rem', fontWeight: 600 },
    h2: { fontSize: '2rem', fontWeight: 600 },
    h3: { fontSize: '1.75rem', fontWeight: 600 },
    h4: { fontSize: '1.5rem', fontWeight: 600 },
    h5: { fontSize: '1.25rem', fontWeight: 600 },
    h6: { fontSize: '1rem', fontWeight: 600 },
    body1: { fontSize: '0.9375rem', lineHeight: 1.6 },
    body2: { fontSize: '0.875rem', lineHeight: 1.5 },
    button: { textTransform: 'none', fontWeight: 500 },
    caption: { fontSize: '0.75rem' },
    overline: { fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.5px' },
  },
  shape: {
    borderRadius: 8,
  },
  shadows: [
    'none',
    '0 1px 2px rgba(0,0,0,0.3)',
    '0 2px 4px rgba(0,0,0,0.3)',
    '0 4px 8px rgba(0,0,0,0.3)',
    '0 8px 16px rgba(0,0,0,0.3)',
    '0 12px 24px rgba(0,0,0,0.3)',
    '0 16px 32px rgba(0,0,0,0.3)',
    '0 20px 40px rgba(0,0,0,0.3)',
    '0 24px 48px rgba(0,0,0,0.3)',
    '0 28px 56px rgba(0,0,0,0.3)',
    '0 32px 64px rgba(0,0,0,0.3)',
    '0 36px 72px rgba(0,0,0,0.3)',
    '0 40px 80px rgba(0,0,0,0.3)',
    '0 44px 88px rgba(0,0,0,0.3)',
    '0 48px 96px rgba(0,0,0,0.3)',
    '0 52px 104px rgba(0,0,0,0.3)',
    '0 56px 112px rgba(0,0,0,0.3)',
    '0 60px 120px rgba(0,0,0,0.3)',
    '0 64px 128px rgba(0,0,0,0.3)',
    '0 68px 136px rgba(0,0,0,0.3)',
    '0 72px 144px rgba(0,0,0,0.3)',
    '0 76px 152px rgba(0,0,0,0.3)',
    '0 80px 160px rgba(0,0,0,0.3)',
    '0 84px 168px rgba(0,0,0,0.3)',
    '0 88px 176px rgba(0,0,0,0.3)',
  ],
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 6,
          padding: '8px 16px',
          fontSize: '0.875rem',
        },
        containedPrimary: {
          '&:hover': { backgroundColor: '#00a17c' },
        },
        containedSecondary: {
          '&:hover': { backgroundColor: '#c63c3c' },
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          backgroundColor: '#161b22',
          border: '1px solid #30363d',
          boxShadow: '0 4px 12px rgba(0,0,0,0.4)',
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundColor: '#161b22',
          border: '1px solid #30363d',
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        root: {
          borderBottom: '1px solid #30363d',
          padding: '12px 16px',
        },
        head: {
          fontWeight: 600,
          backgroundColor: '#0d1117',
          color: '#e6edf3',
        },
      },
    },
    MuiTextField: {
      defaultProps: {
        variant: 'outlined',
        size: 'small',
      },
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            '&:hover fieldset': { borderColor: '#58a6ff' },
            '&.Mui-focused fieldset': { borderColor: '#00d4aa', borderWidth: 2 },
          },
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          fontWeight: 500,
        },
      },
    },
    MuiTooltip: {
      styleOverrides: {
        tooltip: {
          backgroundColor: '#161b22',
          border: '1px solid #30363d',
          fontSize: '0.8rem',
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          backgroundColor: '#161b22',
          borderRight: '1px solid #30363d',
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundColor: '#161b22',
          borderBottom: '1px solid #30363d',
        },
      },
    },
  },
};

export const theme = createTheme(themeOptions);
