'use client';

import React from 'react';

type CardVariant = 'default' | 'elevated' | 'outlined' | 'ghost';
type CardPadding = 'none' | 'sm' | 'md' | 'lg' | 'xl';

const getCardClasses = (variant: CardVariant = 'default', padding: CardPadding = 'md') => {
  const baseClasses = 'rounded-2xl border bg-white shadow-soft';
  
  const variantClasses = {
    default: 'border-gray-200',
    elevated: 'border-gray-200 shadow-soft-lg',
    outlined: 'border-2 border-gray-300',
    ghost: 'border-transparent shadow-none',
  };
  
  const paddingClasses = {
    none: 'p-0',
    sm: 'p-4',
    md: 'p-6',
    lg: 'p-8',
    xl: 'p-10',
  };
  
  return `${baseClasses} ${variantClasses[variant]} ${paddingClasses[padding]}`;
};

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: CardVariant;
  padding?: CardPadding;
}

export const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, variant, padding, ...props }, ref) => {
    const cardClasses = `${getCardClasses(variant, padding)} ${className || ''}`;
    
    return (
      <div
        ref={ref}
        className={cardClasses}
        {...props}
      />
    );
  }
);

Card.displayName = 'Card';

export interface CardHeaderProps extends React.HTMLAttributes<HTMLDivElement> {}

export const CardHeader = React.forwardRef<HTMLDivElement, CardHeaderProps>(
  ({ className, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={`mb-6 ${className || ''}`}
        {...props}
      />
    );
  }
);

CardHeader.displayName = 'CardHeader';

export interface CardTitleProps extends React.HTMLAttributes<HTMLHeadingElement> {}

export const CardTitle = React.forwardRef<HTMLParagraphElement, CardTitleProps>(
  ({ className, ...props }, ref) => {
    return (
      <h3
        ref={ref}
        className={`text-2xl font-semibold leading-none tracking-tight ${className || ''}`}
        {...props}
      />
    );
  }
);

CardTitle.displayName = 'CardTitle';

export interface CardDescriptionProps extends React.HTMLAttributes<HTMLParagraphElement> {}

export const CardDescription = React.forwardRef<HTMLParagraphElement, CardDescriptionProps>(
  ({ className, ...props }, ref) => {
    return (
      <p
        ref={ref}
        className={`text-base text-gray-600 ${className || ''}`}
        {...props}
      />
    );
  }
);

CardDescription.displayName = 'CardDescription';

export interface CardContentProps extends React.HTMLAttributes<HTMLDivElement> {}

export const CardContent = React.forwardRef<HTMLDivElement, CardContentProps>(
  ({ className, ...props }, ref) => {
    return <div ref={ref} className={className} {...props} />;
  }
);

CardContent.displayName = 'CardContent';

export interface CardFooterProps extends React.HTMLAttributes<HTMLDivElement> {}

export const CardFooter = React.forwardRef<HTMLDivElement, CardFooterProps>(
  ({ className, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={`mt-6 pt-6 border-t border-gray-200 ${className || ''}`}
        {...props}
      />
    );
  }
);

CardFooter.displayName = 'CardFooter';