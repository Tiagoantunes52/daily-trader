import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import LoginPage from './LoginPage'

// Mock fetch globally
global.fetch = vi.fn()

// Mock sessionStorage
const mockSessionStorage = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn()
}
Object.defineProperty(window, 'sessionStorage', {
  value: mockSessionStorage
})

// Mock window.location
delete window.location
window.location = { href: '' }

describe('LoginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    window.location.href = ''
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Form Rendering', () => {
    it('renders login form with all required elements', () => {
      render(<LoginPage />)
      
      // Check header elements
      expect(screen.getByText('📈 Daily Market Tips')).toBeInTheDocument()
      expect(screen.getByRole('heading', { name: 'Sign In' })).toBeInTheDocument()
      expect(screen.getByText('Access your personalized market insights')).toBeInTheDocument()
      
      // Check form elements
      expect(screen.getByLabelText('Email Address')).toBeInTheDocument()
      expect(screen.getByLabelText('Password')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Sign In' })).toBeInTheDocument()
      
      // Check OAuth buttons
      expect(screen.getByRole('button', { name: 'Continue with Google' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Continue with GitHub' })).toBeInTheDocument()
      
      // Check footer links
      expect(screen.getByText("Don't have an account?")).toBeInTheDocument()
      expect(screen.getByText('Sign up')).toBeInTheDocument()
      expect(screen.getByText('Forgot your password?')).toBeInTheDocument()
    })

    it('renders form inputs with correct attributes', () => {
      render(<LoginPage />)
      
      const emailInput = screen.getByLabelText('Email Address')
      const passwordInput = screen.getByLabelText('Password')
      
      expect(emailInput).toHaveAttribute('type', 'text')
      expect(emailInput).toHaveAttribute('name', 'email')
      expect(emailInput).toHaveAttribute('autoComplete', 'email')
      expect(emailInput).toHaveAttribute('placeholder', 'Enter your email')
      
      expect(passwordInput).toHaveAttribute('type', 'password')
      expect(passwordInput).toHaveAttribute('name', 'password')
      expect(passwordInput).toHaveAttribute('autoComplete', 'current-password')
      expect(passwordInput).toHaveAttribute('placeholder', 'Enter your password')
    })
  })

  describe('Form Validation', () => {
    it('shows validation errors for empty fields', async () => {
      render(<LoginPage />)
      
      const submitButton = screen.getByRole('button', { name: 'Sign In' })
      fireEvent.click(submitButton)
      
      await waitFor(() => {
        expect(screen.getByText('Email is required')).toBeInTheDocument()
        expect(screen.getByText('Password is required')).toBeInTheDocument()
      })
    })

    it('shows validation error for invalid email format', async () => {
      render(<LoginPage />)
      
      const emailInput = screen.getByLabelText('Email Address')
      const submitButton = screen.getByRole('button', { name: 'Sign In' })
      
      fireEvent.change(emailInput, { target: { value: 'invalid-email' } })
      fireEvent.click(submitButton)
      
      await waitFor(() => {
        expect(screen.getByText('Please enter a valid email address')).toBeInTheDocument()
      })
    })

    it('clears field errors when user starts typing', async () => {
      render(<LoginPage />)
      
      const emailInput = screen.getByLabelText('Email Address')
      const submitButton = screen.getByRole('button', { name: 'Sign In' })
      
      // Trigger validation error
      fireEvent.click(submitButton)
      await waitFor(() => {
        expect(screen.getByText('Email is required')).toBeInTheDocument()
      })
      
      // Start typing to clear error
      fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
      
      await waitFor(() => {
        expect(screen.queryByText('Email is required')).not.toBeInTheDocument()
      })
    })
  })

  describe('Form Submission', () => {
    it('submits form with valid credentials', async () => {
      const mockResponse = {
        ok: true,
        json: vi.fn().mockResolvedValue({ message: 'Login successful' })
      }
      fetch.mockResolvedValue(mockResponse)
      
      render(<LoginPage />)
      
      const emailInput = screen.getByLabelText('Email Address')
      const passwordInput = screen.getByLabelText('Password')
      const submitButton = screen.getByRole('button', { name: 'Sign In' })
      
      fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
      fireEvent.change(passwordInput, { target: { value: 'password123' } })
      fireEvent.click(submitButton)
      
      await waitFor(() => {
        expect(fetch).toHaveBeenCalledWith('/auth/login', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            email: 'test@example.com',
            password: 'password123'
          }),
          credentials: 'include'
        })
      })
      
      await waitFor(() => {
        expect(window.location.href).toBe('/dashboard')
      })
    })

    it('shows loading state during submission', async () => {
      const mockResponse = {
        ok: true,
        json: vi.fn().mockResolvedValue({ message: 'Login successful' })
      }
      fetch.mockResolvedValue(mockResponse)
      
      render(<LoginPage />)
      
      const emailInput = screen.getByLabelText('Email Address')
      const passwordInput = screen.getByLabelText('Password')
      const submitButton = screen.getByRole('button', { name: 'Sign In' })
      
      fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
      fireEvent.change(passwordInput, { target: { value: 'password123' } })
      fireEvent.click(submitButton)
      
      // Check loading state
      expect(screen.getByText('Signing In...')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /signing in/i })).toBeDisabled()
      
      await waitFor(() => {
        expect(window.location.href).toBe('/dashboard')
      })
    })

    it('handles login failure with error message', async () => {
      const mockResponse = {
        ok: false,
        json: vi.fn().mockResolvedValue({ message: 'Invalid credentials' })
      }
      fetch.mockResolvedValue(mockResponse)
      
      render(<LoginPage />)
      
      const emailInput = screen.getByLabelText('Email Address')
      const passwordInput = screen.getByLabelText('Password')
      const submitButton = screen.getByRole('button', { name: 'Sign In' })
      
      fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
      fireEvent.change(passwordInput, { target: { value: 'wrongpassword' } })
      fireEvent.click(submitButton)
      
      await waitFor(() => {
        expect(screen.getByText('Invalid credentials')).toBeInTheDocument()
      })
    })

    it('handles network error', async () => {
      fetch.mockRejectedValue(new Error('Network error'))
      
      render(<LoginPage />)
      
      const emailInput = screen.getByLabelText('Email Address')
      const passwordInput = screen.getByLabelText('Password')
      const submitButton = screen.getByRole('button', { name: 'Sign In' })
      
      fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
      fireEvent.change(passwordInput, { target: { value: 'password123' } })
      fireEvent.click(submitButton)
      
      await waitFor(() => {
        expect(screen.getByText('Network error')).toBeInTheDocument()
      })
    })
  })

  describe('Error Message Display', () => {
    it('displays general error message with proper styling', async () => {
      const mockResponse = {
        ok: false,
        json: vi.fn().mockResolvedValue({ message: 'Server error' })
      }
      fetch.mockResolvedValue(mockResponse)
      
      render(<LoginPage />)
      
      const emailInput = screen.getByLabelText('Email Address')
      const passwordInput = screen.getByLabelText('Password')
      const submitButton = screen.getByRole('button', { name: 'Sign In' })
      
      fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
      fireEvent.change(passwordInput, { target: { value: 'password123' } })
      fireEvent.click(submitButton)
      
      await waitFor(() => {
        const errorMessage = screen.getByText('Server error')
        expect(errorMessage).toBeInTheDocument()
        expect(errorMessage).toHaveAttribute('role', 'alert')
        expect(errorMessage.closest('.general-error')).toBeInTheDocument()
      })
    })

    it('clears general error when user starts typing', async () => {
      const mockResponse = {
        ok: false,
        json: vi.fn().mockResolvedValue({ message: 'Server error' })
      }
      fetch.mockResolvedValue(mockResponse)
      
      render(<LoginPage />)
      
      const emailInput = screen.getByLabelText('Email Address')
      const passwordInput = screen.getByLabelText('Password')
      const submitButton = screen.getByRole('button', { name: 'Sign In' })
      
      fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
      fireEvent.change(passwordInput, { target: { value: 'password123' } })
      fireEvent.click(submitButton)
      
      await waitFor(() => {
        expect(screen.getByText('Server error')).toBeInTheDocument()
      })
      
      // Start typing to clear error
      fireEvent.change(emailInput, { target: { value: 'test2@example.com' } })
      
      await waitFor(() => {
        expect(screen.queryByText('Server error')).not.toBeInTheDocument()
      })
    })
  })

  describe('OAuth Button Functionality', () => {
    it('handles Google OAuth button click', () => {
      render(<LoginPage />)
      
      const googleButton = screen.getByRole('button', { name: 'Continue with Google' })
      fireEvent.click(googleButton)
      
      expect(mockSessionStorage.setItem).toHaveBeenCalledWith('oauth_state', expect.any(String))
      expect(window.location.href).toMatch(/^\/auth\/google\/authorize\?state=/)
    })

    it('handles GitHub OAuth button click', () => {
      render(<LoginPage />)
      
      const githubButton = screen.getByRole('button', { name: 'Continue with GitHub' })
      fireEvent.click(githubButton)
      
      expect(mockSessionStorage.setItem).toHaveBeenCalledWith('oauth_state', expect.any(String))
      expect(window.location.href).toMatch(/^\/auth\/github\/authorize\?state=/)
    })

    it('generates different state parameters for each OAuth request', () => {
      render(<LoginPage />)
      
      const googleButton = screen.getByRole('button', { name: 'Continue with Google' })
      const githubButton = screen.getByRole('button', { name: 'Continue with GitHub' })
      
      fireEvent.click(googleButton)
      const firstState = mockSessionStorage.setItem.mock.calls[0][1]
      
      fireEvent.click(githubButton)
      const secondState = mockSessionStorage.setItem.mock.calls[1][1]
      
      expect(firstState).not.toBe(secondState)
      expect(firstState).toMatch(/^[a-z0-9]+$/)
      expect(secondState).toMatch(/^[a-z0-9]+$/)
    })

    it('disables OAuth buttons during form submission', async () => {
      const mockResponse = {
        ok: true,
        json: vi.fn().mockResolvedValue({ message: 'Login successful' })
      }
      fetch.mockResolvedValue(mockResponse)
      
      render(<LoginPage />)
      
      const emailInput = screen.getByLabelText('Email Address')
      const passwordInput = screen.getByLabelText('Password')
      const submitButton = screen.getByRole('button', { name: 'Sign In' })
      const googleButton = screen.getByRole('button', { name: 'Continue with Google' })
      const githubButton = screen.getByRole('button', { name: 'Continue with GitHub' })
      
      fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
      fireEvent.change(passwordInput, { target: { value: 'password123' } })
      fireEvent.click(submitButton)
      
      // Check that OAuth buttons are disabled during loading
      expect(googleButton).toBeDisabled()
      expect(githubButton).toBeDisabled()
      
      await waitFor(() => {
        expect(window.location.href).toBe('/dashboard')
      })
    })
  })
})