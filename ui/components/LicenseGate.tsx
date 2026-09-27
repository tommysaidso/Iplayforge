import React, { useState } from 'react';
import { X, Sparkles, Lock } from 'lucide-react';
import { licenseApi, LicenseStatus } from '../services/api';

const BUY_URL = 'https://iplay.studio/#access';

/**
 * Ben, 2026-09-27: "users in this beta stage can access and use but gotta
 * pay for our time.. and we are true..no watermark if you own it, we love
 * to give tools but everything has a test n a pay the man moment, thas jus
 * business." One free watermarked preview, then subscribe or buy the rig.
 * Mirrors the Windows plugin's gate (D:\OSTERTOG_Music\iplay_plugin\static\index.html).
 */

interface TrialBannerProps {
  licenseStatus: LicenseStatus | null;
  onActivateClick: () => void;
}

/** Slim, non-blocking strip shown while a free preview is still available. */
export const TrialBanner: React.FC<TrialBannerProps> = ({ licenseStatus, onActivateClick }) => {
  if (!licenseStatus || licenseStatus.license_ok || !licenseStatus.trial_available) return null;

  return (
    <div className="flex items-center gap-3 px-4 py-2.5 bg-amber-500/10 border-b border-amber-500/20 text-sm text-amber-200">
      <Sparkles size={16} className="flex-shrink-0 text-amber-400" />
      <span className="flex-1">
        Free preview mode — <b>one</b> short, watermarked song before you need a license.
      </span>
      <button
        onClick={onActivateClick}
        className="flex-shrink-0 underline decoration-amber-400/50 hover:decoration-amber-400 font-medium"
      >
        Subscribe or buy the rig
      </button>
    </div>
  );
};

interface LicenseGateModalProps {
  isOpen: boolean;
  onClose: () => void;
  licenseStatus: LicenseStatus | null;
  onActivated: (status: LicenseStatus) => void;
}

/**
 * Full gate — opened either by clicking the banner, or automatically when a
 * generation attempt 402s with reason "trial_used" or "trial_scope". Unlike
 * the trial banner this can be dismissed (onClose) even while gated; the
 * backend, not this modal, is what actually stops another free build.
 */
export const LicenseGateModal: React.FC<LicenseGateModalProps> = ({ isOpen, onClose, licenseStatus, onActivated }) => {
  const [key, setKey] = useState('');
  const [error, setError] = useState('');
  const [activating, setActivating] = useState(false);

  if (!isOpen) return null;

  const trialSpent = !!licenseStatus && !licenseStatus.license_ok && !licenseStatus.trial_available;

  const handleActivate = async () => {
    const trimmed = key.trim();
    if (!trimmed) {
      setError('Paste your license key.');
      return;
    }
    setError('');
    setActivating(true);
    try {
      await licenseApi.activate(trimmed);
      const fresh = await licenseApi.status();
      onActivated(fresh);
    } catch (e) {
      setError(e instanceof Error ? e.message.replace(/^\d+:\s*/, '') : 'Activation failed.');
    } finally {
      setActivating(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div
        className="bg-white dark:bg-zinc-900 rounded-2xl shadow-2xl max-w-md w-full overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-6">
          <div className="flex items-start justify-between mb-2">
            <div className="flex items-center gap-2 text-zinc-900 dark:text-white">
              <Lock size={18} />
              <h2 className="text-lg font-bold">
                {trialSpent ? 'Free preview used' : 'Activate your studio'}
              </h2>
            </div>
            <button onClick={onClose} className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200">
              <X size={20} />
            </button>
          </div>
          <p className="text-sm text-zinc-500 dark:text-zinc-400 mb-4">
            {trialSpent
              ? "You've used this install's one free song. Subscribe or buy the rig for unlimited, unwatermarked songs — or paste a license key below if you already have one."
              : 'iplayForge runs on your own GPU with your paid account. Paste the license key from your account to unlock unlimited, unwatermarked songs.'}
          </p>

          <a
            href={BUY_URL}
            target="_blank"
            rel="noreferrer"
            className="block text-center w-full px-4 py-2.5 mb-4 bg-zinc-900 dark:bg-white text-white dark:text-black font-semibold rounded-lg hover:bg-zinc-800 dark:hover:bg-zinc-200 transition-colors"
          >
            Subscribe or buy the rig →
          </a>

          <div className="text-xs uppercase tracking-wide text-zinc-400 dark:text-zinc-500 mb-2">
            Already have a license key?
          </div>
          <input
            type="text"
            value={key}
            onChange={(e) => setKey(e.target.value)}
            placeholder="paste your license key"
            className="w-full px-3 py-2 rounded-lg border border-zinc-200 dark:border-white/10 bg-zinc-50 dark:bg-zinc-800 text-zinc-900 dark:text-white text-sm mb-2"
          />
          {error && <div className="text-xs text-red-500 mb-2">{error}</div>}
          <button
            onClick={handleActivate}
            disabled={activating}
            className="w-full px-4 py-2 bg-zinc-100 dark:bg-white/10 text-zinc-900 dark:text-white font-semibold rounded-lg hover:bg-zinc-200 dark:hover:bg-white/20 transition-colors disabled:opacity-50"
          >
            {activating ? 'Activating…' : 'Activate'}
          </button>
        </div>
      </div>
    </div>
  );
};
