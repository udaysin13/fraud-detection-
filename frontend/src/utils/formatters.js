/**
 * VaultGuard - Common Formatters & Helpers
 * Supports Indian Rupee (INR) formatting, Indian timestamp presentation,
 * and standardized risk category styling.
 */

/**
 * Formats a numeric value into Indian Rupee currency format (e.g. ₹1,23,456.50).
 */
export const formatINR = (value, options = {}) => {
  if (value === null || value === undefined || isNaN(value)) {
    return '₹0.00';
  }
  const num = Number(value);
  const showDecimals = options.decimals ?? true;

  try {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      minimumFractionDigits: showDecimals ? 2 : 0,
      maximumFractionDigits: showDecimals ? 2 : 0,
    }).format(num);
  } catch {
    return `₹${num.toFixed(2)}`;
  }
};

/**
 * Formats an integer or float with Indian numbering system (e.g. 1,50,000).
 */
export const formatIndianNumber = (value) => {
  if (value === null || value === undefined || isNaN(value)) {
    return '0';
  }
  return new Intl.NumberFormat('en-IN').format(Number(value));
};

/**
 * Formats an ISO or SQL timestamp into legible presentation.
 */
export const formatTimestamp = (timestampStr) => {
  if (!timestampStr) return '—';
  try {
    const date = new Date(timestampStr);
    if (isNaN(date.getTime())) {
      // In case string format is "YYYY-MM-DD HH:mm:ss"
      return timestampStr;
    }
    return new Intl.DateTimeFormat('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    }).format(date);
  } catch {
    return timestampStr;
  }
};

/**
 * Maps decision or risk score to visual badge colors.
 * Green for low risk, Amber for review, Red for high risk.
 */
export const getRiskStyle = (decision, score = 0) => {
  const normDecision = (decision || '').toLowerCase();

  if (normDecision.includes('block') || score > 70) {
    return {
      bg: 'bg-rose-500/10',
      border: 'border-rose-500/30',
      text: 'text-rose-600 dark:text-rose-400',
      pill: 'bg-rose-500 text-white',
      label: 'High Risk / Block',
      category: 'HIGH_RISK',
      badgeColor: 'rose',
    };
  }

  if (normDecision.includes('review') || (score > 40 && score <= 70)) {
    return {
      bg: 'bg-amber-500/10',
      border: 'border-amber-500/30',
      text: 'text-amber-600 dark:text-amber-400',
      pill: 'bg-amber-500 text-white',
      label: 'Manual Review',
      category: 'REVIEW',
      badgeColor: 'amber',
    };
  }

  return {
    bg: 'bg-emerald-500/10',
    border: 'border-emerald-500/30',
    text: 'text-emerald-600 dark:text-emerald-400',
    pill: 'bg-emerald-500 text-white',
    label: 'Low Risk / Allow',
    category: 'LOW_RISK',
    badgeColor: 'emerald',
  };
};

/**
 * Returns human-friendly label for Indian payment channels.
 */
export const getChannelLabel = (channel) => {
  switch (channel) {
    case 'UPI_P2P':
      return 'UPI P2P Transfer';
    case 'UPI_P2M_QR':
      return 'UPI P2M QR Merchant';
    case 'WALLET':
      return 'Digital Wallet';
    case 'IMPS':
      return 'IMPS Fast Transfer';
    case 'RUPAY_CARD':
      return 'RuPay Debit/Credit';
    default:
      return channel || 'UPI Payment';
  }
};
