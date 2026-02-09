/**
 * License Manager for Undectr
 * Handles license verification, activation, and server communication
 */

import { app } from 'electron';
import path from 'path';
import fs from 'fs';
import crypto from 'crypto';
import os from 'os';

export interface LicenseInfo {
  license_key: string;
  tier: 'free' | 'pro' | 'lifetime' | 'studio';
  customer_email?: string;
  customer_name?: string;
  price_paid: number;
  currency: string;
  status: 'active' | 'pending' | 'expired' | 'revoked';
  activated: boolean;
  activation_date?: string;
  expires_at?: string;
  max_activations: number;
  current_activations: number;
  machine_id?: string;
  metadata?: Record<string, any>;
}

export interface VerificationResult {
  valid: boolean;
  license?: LicenseInfo;
  message: string;
  error_code?: string;
  server_response?: any;
}

export interface PurchaseResult {
  success: boolean;
  payment_url?: string;
  reference_id?: string;
  license_key?: string;
  message?: string;
}

export class LicenseManager {
  private licensePath: string;
  private usagePath: string;
  private serverUrl: string;
  private machineId: string;

  constructor() {
    const userDataPath = app.getPath('userData');
    this.licensePath = path.join(userDataPath, 'license.json');
    this.usagePath = path.join(userDataPath, 'usage.json');
    this.serverUrl = process.env.LICENSE_SERVER_URL || 'http://localhost:3000';
    this.machineId = this.generateMachineId();
    
    // Ensure directories exist
    this.ensureDirectories();
  }

  private ensureDirectories(): void {
    const licenseDir = path.dirname(this.licensePath);
    if (!fs.existsSync(licenseDir)) {
      fs.mkdirSync(licenseDir, { recursive: true });
    }
  }

  private generateMachineId(): string {
    // Generate a unique machine ID based on system information
    const machineInfo = {
      hostname: os.hostname(),
      platform: os.platform(),
      arch: os.arch(),
      cpus: os.cpus().length,
      totalMem: os.totalmem(),
    };
    
    const machineString = JSON.stringify(machineInfo);
    const hash = crypto.createHash('sha256').update(machineString).digest('hex').substring(0, 32);
    
    return `machine_${hash}`;
  }

  private async makeRequest(endpoint: string, method: string = 'GET', data?: any): Promise<any> {
    const url = `${this.serverUrl}${endpoint}`;
    
    try {
      const response = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
          'User-Agent': `SunoStudioPro/${app.getVersion()} (${process.platform})`,
        },
        body: data ? JSON.stringify(data) : undefined,
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      return await response.json();
    } catch (error: any) {
      console.error(`Request failed to ${url}:`, error);
      throw error;
    }
  }

  async getLicenseInfo(): Promise<LicenseInfo | null> {
    try {
      if (fs.existsSync(this.licensePath)) {
        const data = fs.readFileSync(this.licensePath, 'utf8');
        const license = JSON.parse(data);
        
        // Verify with server if online
        try {
          const result = await this.verifyLicense(license.license_key);
          if (result.valid && result.license) {
            // Update local license with server data
            this.saveLicense(result.license);
            return result.license;
          } else {
            // License invalid on server, but we still return local copy
            console.warn('License server verification failed:', result.message);
          }
        } catch (error) {
          // Server offline, use local license
          console.warn('License server unavailable, using local license');
        }
        
        return license;
      }
    } catch (error) {
      console.error('Error reading license:', error);
    }
    
    return null;
  }

  async saveLicense(license: LicenseInfo): Promise<void> {
    try {
      fs.writeFileSync(this.licensePath, JSON.stringify(license, null, 2));
    } catch (error) {
      console.error('Error saving license:', error);
      throw error;
    }
  }

  async verifyLicense(licenseKey: string): Promise<VerificationResult> {
    try {
      const response = await this.makeRequest('/api/verify', 'POST', {
        license_key: licenseKey,
        machine_id: this.machineId,
      });

      if (response.valid) {
        const license: LicenseInfo = {
          license_key: licenseKey,
          tier: response.license.tier || 'pro',
          customer_email: response.license.customer_email,
          customer_name: response.license.customer_name,
          price_paid: response.license.price_paid || 0,
          currency: response.license.currency || 'USD',
          status: response.license.status || 'active',
          activated: true,
          activation_date: response.license.activation_date || new Date().toISOString(),
          expires_at: response.license.expires_at,
          max_activations: response.license.max_activations || 1,
          current_activations: response.license.current_activations || 1,
          machine_id: this.machineId,
          metadata: response.license.metadata || {},
        };

        // Save verified license locally
        await this.saveLicense(license);

        return {
          valid: true,
          license,
          message: response.message || 'License verified successfully',
          server_response: response,
        };
      } else {
        return {
          valid: false,
          message: response.message || 'License verification failed',
          error_code: response.error_code,
          server_response: response,
        };
      }
    } catch (error: any) {
      console.error('License verification error:', error);
      
      // Fallback to local verification if server is unreachable
      if (fs.existsSync(this.licensePath)) {
        const data = fs.readFileSync(this.licensePath, 'utf8');
        const localLicense = JSON.parse(data);
        
        if (localLicense.license_key === licenseKey) {
          // Check if license is expired
          if (localLicense.expires_at) {
            const expires = new Date(localLicense.expires_at);
            if (new Date() > expires) {
              return {
                valid: false,
                message: 'License has expired',
                error_code: 'LICENSE_EXPIRED',
              };
            }
          }
          
          return {
            valid: true,
            license: localLicense,
            message: 'License verified locally (server unreachable)',
            error_code: 'SERVER_OFFLINE',
          };
        }
      }
      
      return {
        valid: false,
        message: error.message || 'License verification failed',
        error_code: 'NETWORK_ERROR',
      };
    }
  }

  async activateLicense(licenseKey: string, machineName?: string): Promise<VerificationResult> {
    try {
      if (!machineName) {
        machineName = `${os.platform()} ${os.release()}`;
      }

      const response = await this.makeRequest('/api/activate', 'POST', {
        license_key: licenseKey,
        machine_id: this.machineId,
        machine_name: machineName,
      });

      if (response.success) {
        // Get updated license info
        const verification = await this.verifyLicense(licenseKey);
        
        if (verification.valid && verification.license) {
          return verification;
        } else {
          return {
            valid: false,
            message: 'Activation succeeded but verification failed',
            error_code: 'VERIFICATION_FAILED',
            server_response: response,
          };
        }
      } else {
        return {
          valid: false,
          message: response.message || 'License activation failed',
          error_code: response.error_code || 'ACTIVATION_FAILED',
          server_response: response,
        };
      }
    } catch (error: any) {
      console.error('License activation error:', error);
      return {
        valid: false,
        message: error.message || 'License activation failed',
        error_code: 'NETWORK_ERROR',
      };
    }
  }

  async deactivateLicense(licenseKey: string): Promise<{ success: boolean; message: string }> {
    try {
      const response = await this.makeRequest('/api/deactivate', 'POST', {
        license_key: licenseKey,
        machine_id: this.machineId,
      });

      if (response.success) {
        // Remove local license
        if (fs.existsSync(this.licensePath)) {
          fs.unlinkSync(this.licensePath);
        }
        
        return {
          success: true,
          message: response.message || 'License deactivated successfully',
        };
      } else {
        return {
          success: false,
          message: response.message || 'License deactivation failed',
        };
      }
    } catch (error: any) {
      console.error('License deactivation error:', error);
      return {
        success: false,
        message: error.message || 'License deactivation failed',
      };
    }
  }

  async purchaseLicense(tier: 'pro' | 'lifetime' | 'studio', paymentMethod: 'usdc' | 'crypto', email: string, name?: string): Promise<PurchaseResult> {
    try {
      const response = await this.makeRequest('/api/checkout', 'POST', {
        tier,
        email,
        name,
        payment_method: paymentMethod,
      });

      if (response.success) {
        return {
          success: true,
          payment_url: response.payment_url,
          reference_id: response.reference_id,
          license_key: response.license_key,
          message: response.message || 'Checkout created successfully',
        };
      } else {
        return {
          success: false,
          message: response.message || 'Purchase failed',
        };
      }
    } catch (error: any) {
      console.error('Purchase error:', error);
      return {
        success: false,
        message: error.message || 'Purchase failed',
      };
    }
  }

  async checkLicenseStatus(licenseKey: string): Promise<LicenseInfo | null> {
    try {
      const response = await this.makeRequest(`/api/licenses/${licenseKey}`);
      
      if (response) {
        const license: LicenseInfo = {
          license_key: licenseKey,
          tier: response.tier || 'pro',
          customer_email: response.customer_email,
          customer_name: response.customer_name,
          price_paid: response.price_paid || 0,
          currency: response.currency || 'USD',
          status: response.status || 'active',
          activated: response.activated || false,
          activation_date: response.activation_date,
          expires_at: response.expires_at,
          max_activations: response.max_activations || 1,
          current_activations: response.current_activations || 0,
          metadata: response.metadata || {},
        };
        
        return license;
      }
    } catch (error) {
      console.error('License status check error:', error);
    }
    
    return null;
  }

  async checkUsageLimits(): Promise<{ can_process: boolean; message: string }> {
    const license = await this.getLicenseInfo();
    
    if (!license) {
      // No license = free tier
      const usage = await this.getUsage();
      if (usage.tracks_this_month >= 5) {
        return {
          can_process: false,
          message: 'Free tier limit reached (5 tracks per month). Please upgrade.',
        };
      }
      return { can_process: true, message: 'Free tier: tracks remaining' };
    }
    
    if (license.tier === 'free') {
      const usage = await this.getUsage();
      if (usage.tracks_this_month >= 5) {
        return {
          can_process: false,
          message: 'Free tier limit reached (5 tracks per month). Please upgrade.',
        };
      }
    }
    
    // Check if license is valid
    if (license.status !== 'active') {
      return {
        can_process: false,
        message: `License status: ${license.status}. Please contact support.`,
      };
    }
    
    // Check expiration
    if (license.expires_at) {
      const expires = new Date(license.expires_at);
      if (new Date() > expires) {
        return {
          can_process: false,
          message: 'License has expired. Please renew.',
        };
      }
    }
    
    // Check activation
    if (!license.activated) {
      return {
        can_process: false,
        message: 'License not activated on this machine.',
      };
    }
    
    return { can_process: true, message: 'License valid' };
  }

  async getUsage(): Promise<{ tracks_this_month: number; month: number }> {
    try {
      if (fs.existsSync(this.usagePath)) {
        const data = fs.readFileSync(this.usagePath, 'utf8');
        const usage = JSON.parse(data);
        
        // Reset if new month
        const currentMonth = new Date().getMonth();
        if (usage.month !== currentMonth) {
          usage.tracks_this_month = 0;
          usage.month = currentMonth;
          fs.writeFileSync(this.usagePath, JSON.stringify(usage, null, 2));
        }
        
        return usage;
      }
    } catch (error) {
      console.error('Error reading usage:', error);
    }
    
    // Default usage
    return {
      tracks_this_month: 0,
      month: new Date().getMonth(),
    };
  }

  async incrementUsage(): Promise<void> {
    try {
      const usage = await this.getUsage();
      usage.tracks_this_month++;
      
      const usageDir = path.dirname(this.usagePath);
      if (!fs.existsSync(usageDir)) {
        fs.mkdirSync(usageDir, { recursive: true });
      }
      
      fs.writeFileSync(this.usagePath, JSON.stringify(usage, null, 2));
    } catch (error) {
      console.error('Error incrementing usage:', error);
    }
  }

  clearLicense(): void {
    if (fs.existsSync(this.licensePath)) {
      fs.unlinkSync(this.licensePath);
    }
  }

  getMachineId(): string {
    return this.machineId;
  }

  getServerUrl(): string {
    return this.serverUrl;
  }

  async testServerConnection(): Promise<boolean> {
    try {
      const response = await fetch(`${this.serverUrl}/health`);
      return response.ok;
    } catch {
      return false;
    }
  }
}

// Singleton instance
let licenseManagerInstance: LicenseManager | null = null;

export function getLicenseManager(): LicenseManager {
  if (!licenseManagerInstance) {
    licenseManagerInstance = new LicenseManager();
  }
  return licenseManagerInstance;
}