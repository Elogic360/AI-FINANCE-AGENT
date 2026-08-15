import { useState, useEffect } from 'react';
import { CheckCircle, XCircle, AlertTriangle, Info, X } from 'lucide-react';

type AlertVariant = 'success' | 'error' | 'warning' | 'info';

interface AlertProps {
  variant: AlertVariant;
  title?: string;
  children: React.ReactNode;
  dismissible?: boolean;
  autoDismiss?: number;
  onDismiss?: () => void;
  className?: string;
}

const variantConfig = {
  success: {
    icon: CheckCircle,
    bg: 'bg-green-500/10',
    border: 'border-green-500/30',
    text: 'text-green-400',
    iconColor: 'text-green-400',
  },
  error: {
    icon: XCircle,
    bg: 'bg-red-500/10',
    border: 'border-red-500/30',
    text: 'text-red-400',
    iconColor: 'text-red-400',
  },
  warning: {
    icon: AlertTriangle,
    bg: 'bg-amber-500/10',
    border: 'border-amber-500/30',
    text: 'text-amber-400',
    iconColor: 'text-amber-400',
  },
  info: {
    icon: Info,
    bg: 'bg-blue-500/10',
    border: 'border-blue-500/30',
    text: 'text-blue-400',
    iconColor: 'text-blue-400',
  },
};

export default function Alert({
  variant,
  title,
  children,
  dismissible = false,
  autoDismiss,
  onDismiss,
  className = '',
}: AlertProps) {
  const [visible, setVisible] = useState(true);
  const config = variantConfig[variant];
  const IconComp = config.icon;

  useEffect(() => {
    if (autoDismiss && autoDismiss > 0) {
      const timer = setTimeout(() => {
        setVisible(false);
        onDismiss?.();
      }, autoDismiss);
      return () => clearTimeout(timer);
    }
  }, [autoDismiss, onDismiss]);

  if (!visible) return null;

  const handleDismiss = () => {
    setVisible(false);
    onDismiss?.();
  };

  return (
    <div
      className={`${config.bg} border ${config.border} rounded-xl px-4 py-3 flex items-start gap-3 animate-fade-in ${className}`}
      role="alert"
    >
      <IconComp size={18} className={`${config.iconColor} shrink-0 mt-0.5`} />
      <div className="flex-1 min-w-0">
        {title && <div className={`${config.text} font-medium text-sm mb-0.5`}>{title}</div>}
        <div className={`${config.text} text-sm opacity-90`}>{children}</div>
      </div>
      {dismissible && (
        <button
          onClick={handleDismiss}
          className={`${config.text} opacity-60 hover:opacity-100 p-0.5 rounded transition shrink-0`}
          aria-label="Dismiss"
        >
          <X size={16} />
        </button>
      )}
    </div>
  );
}
