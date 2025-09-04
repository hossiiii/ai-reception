'use client';

import React from 'react';

type ButtonVariant = 'primary' | 'secondary' | 'outline' | 'ghost' | 'destructive';
type ButtonSize = 'sm' | 'md' | 'lg' | 'xl';

const getButtonClasses = (variant: ButtonVariant = 'primary', size: ButtonSize = 'md') => {
  const baseClasses = 'inline-flex items-center justify-center rounded-xl font-medium transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50';
  
  const variantClasses = {
    primary: 'bg-primary-600 text-white hover:bg-primary-700 shadow-md hover:shadow-lg focus-visible:ring-primary-500',
    secondary: 'bg-white text-gray-900 border border-gray-300 hover:bg-gray-50 focus-visible:ring-primary-500',
    outline: 'border border-gray-300 bg-transparent hover:bg-gray-100 focus-visible:ring-primary-500',
    ghost: 'hover:bg-gray-100 focus-visible:ring-primary-500',
    destructive: 'bg-red-600 text-white hover:bg-red-700 shadow-md hover:shadow-lg focus-visible:ring-red-500',
  };
  
  const sizeClasses = {
    sm: 'h-10 px-4 py-2 text-sm',
    md: 'h-12 px-6 py-3 text-base',
    lg: 'h-14 px-8 py-4 text-lg',
    xl: 'h-16 px-10 py-5 text-xl',
  };
  
  return `${baseClasses} ${variantClasses[variant]} ${sizeClasses[size]}`;
};

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  icon?: React.ReactNode;
  iconPosition?: 'left' | 'right';
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, loading, icon, iconPosition = 'left', children, disabled, ...props }, ref) => {
    const buttonClasses = `${getButtonClasses(variant, size)} ${className || ''}`;
    
    return (
      <button
        className={buttonClasses}
        ref={ref}
        disabled={disabled || loading}
        {...props}
      >
        {loading && (
          <div className="mr-2 h-4 w-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
        )}
        {!loading && icon && iconPosition === 'left' && (
          <span className="mr-2">{icon}</span>
        )}
        {children}
        {!loading && icon && iconPosition === 'right' && (
          <span className="ml-2">{icon}</span>
        )}
      </button>
    );
  }
);

Button.displayName = 'Button';