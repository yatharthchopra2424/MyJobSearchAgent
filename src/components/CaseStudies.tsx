import React from 'react';
import { ArrowRight } from 'lucide-react';

interface CaseStudyProps {
  image: string;
  category: string;
  title: string;
  description: string;
}

const CaseStudy: React.FC<CaseStudyProps> = ({ image, category, title, description }) => {
  return (
    <div className="group relative overflow-hidden rounded-xl bg-white dark:bg-gray-800 shadow-sm hover:shadow-md transition-all">
      <div className="h-64 overflow-hidden">
        <img 
          src={image} 
          alt={title} 
          className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
        />
      </div>
      <div className="p-6">
        <span className="inline-block px-3 py-1 text-sm font-medium text-blue-600 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/30 rounded-full mb-3">
          {category}
        </span>
        <h3 className="text-xl font-semibold mb-3 text-gray-900 dark:text-white">{title}</h3>
        <p className="text-gray-600 dark:text-gray-300 mb-4">{description}</p>
        <a 
          href="#" 
          className="inline-flex items-center text-blue-600 dark:text-blue-400 font-medium hover:text-blue-700 dark:hover:text-blue-300 group/link"
        >
          Read Case Study
          <ArrowRight size={16} className="ml-2 transition-transform group-hover/link:translate-x-1" />
        </a>
      </div>
    </div>
  );
};

const CaseStudies: React.FC = () => {
  const caseStudies = [
    {
      image: "https://images.pexels.com/photos/3184465/pexels-photo-3184465.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=2",
      category: "Finance",
      title: "AI-Powered Fraud Detection System",
      description: "How we helped a leading financial institution reduce fraud by 87% using our advanced machine learning algorithms."
    },
    {
      image: "https://images.pexels.com/photos/8985454/pexels-photo-8985454.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=2",
      category: "Healthcare",
      title: "Predictive Analytics for Patient Care",
      description: "Implementing AI to predict patient outcomes and optimize treatment plans, resulting in 32% better recovery rates."
    },
    {
      image: "https://images.pexels.com/photos/5483077/pexels-photo-5483077.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=2",
      category: "Retail",
      title: "Intelligent Inventory Management",
      description: "How our AI solution helped a retail chain reduce inventory costs by 23% while improving product availability."
    }
  ];

  return (
    <section id="case-studies" className="py-20 bg-white dark:bg-gray-900">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-end mb-12">
          <div className="max-w-2xl mb-6 md:mb-0">
            <span className="text-blue-600 dark:text-blue-400 font-medium">Case Studies</span>
            <h2 className="text-3xl md:text-4xl font-bold mt-2 mb-4 text-gray-900 dark:text-white">
              Our Success Stories
            </h2>
            <p className="text-gray-600 dark:text-gray-300 text-lg">
              See how our AI solutions have transformed businesses across different industries.
            </p>
          </div>
          <a 
            href="#" 
            className="inline-flex items-center text-blue-600 dark:text-blue-400 font-medium hover:text-blue-700 dark:hover:text-blue-300"
          >
            View All Case Studies
            <ArrowRight size={16} className="ml-2" />
          </a>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {caseStudies.map((study, index) => (
            <CaseStudy 
              key={index}
              image={study.image}
              category={study.category}
              title={study.title}
              description={study.description}
            />
          ))}
        </div>
      </div>
    </section>
  );
};

export default CaseStudies;