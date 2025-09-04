'use client';

import React from 'react';

type InputVariant = 'default' | 'error' | 'success';
type InputSize = 'sm' | 'md' | 'lg';

const getInputClasses = (variant: InputVariant = 'default', size: InputSize = 'md') => {
  const baseClasses = 'flex w-full rounded-xl border bg-white px-4 py-3 text-base placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 transition-colors';
  
  const variantClasses = {
    default: 'border-gray-300 focus:border-primary-500 focus:ring-primary-500',
    error: 'border-red-500 focus:border-red-500 focus:ring-red-500',
    success: 'border-green-500 focus:border-green-500 focus:ring-green-500',
  };
  
  const sizeClasses = {
    sm: 'h-10 px-3 py-2 text-sm',
    md: 'h-12 px-4 py-3 text-base',
    lg: 'h-14 px-6 py-4 text-lg',
  };
  
  return `${baseClasses} ${variantClasses[variant]} ${sizeClasses[size]}`;
};

export interface InputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'size'> {
  variant?: InputVariant;
  size?: InputSize;
  label?: string;
  error?: string;
  helpText?: string;
  icon?: React.ReactNode;
  iconPosition?: 'left' | 'right';
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, variant, size, label, error, helpText, icon, iconPosition = 'left', id, ...props }, ref) => {
    const generatedId = React.useId();
    const inputId = id || generatedId;
    const errorId = React.useId();
    const helpTextId = React.useId();

    return (
      <div className="space-y-2">
        {label && (
          <label
            htmlFor={inputId}
            className="block text-base font-medium text-gray-900"
          >
            {label}
            {props.required && <span className="text-red-500 ml-1">*</span>}
          </label>
        )}
        
        <div className="relative">
          {icon && iconPosition === 'left' && (
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <div className="h-5 w-5 text-gray-400">
                {icon}
              </div>
            </div>
          )}
          
          <input
            id={inputId}
            className={`${getInputClasses(error ? 'error' : variant, size)} ${
                icon && iconPosition === 'left' ? 'pl-10' : ''
              } ${
                icon && iconPosition === 'right' ? 'pr-10' : ''
              } ${className || ''}`}
            ref={ref}
            aria-describedby={
              error ? errorId : helpText ? helpTextId : undefined
            }
            aria-invalid={error ? 'true' : 'false'}
            {...props}
          />
          
          {icon && iconPosition === 'right' && (
            <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
              <div className="h-5 w-5 text-gray-400">
                {icon}
              </div>
            </div>
          )}
        </div>
        
        {error && (
          <p id={errorId} className="text-sm text-red-600">
            {error}
          </p>
        )}
        
        {helpText && !error && (
          <p id={helpTextId} className="text-sm text-gray-500">
            {helpText}
          </p>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';

export interface TextareaProps
  extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
  helpText?: string;
}

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, label, error, helpText, id, ...props }, ref) => {
    const generatedId = React.useId();
    const textareaId = id || generatedId;
    const errorId = React.useId();
    const helpTextId = React.useId();

    return (
      <div className="space-y-2">
        {label && (
          <label
            htmlFor={textareaId}
            className="block text-base font-medium text-gray-900"
          >
            {label}
            {props.required && <span className="text-red-500 ml-1">*</span>}
          </label>
        )}
        
        <textarea
          id={textareaId}
          className={`flex min-h-[80px] w-full rounded-xl border border-gray-300 bg-white px-4 py-3 text-base placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 disabled:cursor-not-allowed disabled:opacity-50 transition-colors resize-none ${
            error ? 'border-red-500 focus:border-red-500 focus:ring-red-500' : ''
          } ${className || ''}`}
          ref={ref}
          aria-describedby={
            error ? errorId : helpText ? helpTextId : undefined
          }
          aria-invalid={error ? 'true' : 'false'}
          {...props}
        />
        
        {error && (
          <p id={errorId} className="text-sm text-red-600">
            {error}
          </p>
        )}
        
        {helpText && !error && (
          <p id={helpTextId} className="text-sm text-gray-500">
            {helpText}
          </p>
        )}
      </div>
    );
  }
);

Textarea.displayName = 'Textarea';