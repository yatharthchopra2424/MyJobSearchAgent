import React, { useState } from 'react';
import { ChevronLeft, ChevronRight, Star } from 'lucide-react';

interface TestimonialProps {
  content: string;
  name: string;
  role: string;
  company: string;
  image: string;
}

const Testimonial: React.FC<TestimonialProps> = ({ content, name, role, company, image }) => {
  return (
    <div className="bg-white dark:bg-gray-800 p-8 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700">
      <div className="flex gap-1 mb-6">
        {[...Array(5)].map((_, i) => (
          <Star key={i} size={18} className="text-yellow-400 fill-yellow-400" />
        ))}
      </div>
      <p className="text-gray-700 dark:text-gray-300 text-lg leading-relaxed mb-6">
        "{content}"
      </p>
      <div className="flex items-center">
        <img 
          src={image} 
          alt={name} 
          className="w-12 h-12 rounded-full object-cover mr-4"
        />
        <div>
          <h4 className="font-semibold text-gray-900 dark:text-white">{name}</h4>
          <p className="text-gray-500 dark:text-gray-400 text-sm">{role}, {company}</p>
        </div>
      </div>
    </div>
  );
};

const Testimonials: React.FC = () => {
  const [currentSlide, setCurrentSlide] = useState(0);
  
  const testimonials = [
    {
      content: "Agile Partners AI has revolutionized how we handle customer data. Their predictive analytics solution has increased our conversion rates by 45% in just three months.",
      name: "Sarah Johnson",
      role: "CTO",
      company: "TechVision Inc.",
      image: "https://images.pexels.com/photos/762020/pexels-photo-762020.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=2"
    },
    {
      content: "The AI-powered automation system developed by Agile Partners has reduced our operational costs by 30% while improving accuracy. Their team's expertise is unmatched.",
      name: "Michael Chen",
      role: "Operations Director",
      company: "Global Logistics",
      image: "https://images.pexels.com/photos/1516680/pexels-photo-1516680.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=2"
    },
    {
      content: "Implementing Agile Partners' AI solutions has been a game-changer for our healthcare facility. Patient satisfaction is up by 28% and our diagnostic accuracy has significantly improved.",
      name: "Dr. Emily Rodriguez",
      role: "Medical Director",
      company: "Highland Medical Center",
      image: "https://images.pexels.com/photos/5397723/pexels-photo-5397723.jpeg?auto=compress&cs=tinysrgb&w=1260&h=750&dpr=2"
    }
  ];

  const nextSlide = () => {
    setCurrentSlide((prev) => (prev === testimonials.length - 1 ? 0 : prev + 1));
  };

  const prevSlide = () => {
    setCurrentSlide((prev) => (prev === 0 ? testimonials.length - 1 : prev - 1));
  };

  return (
    <section className="py-20 bg-gray-50 dark:bg-gray-900">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <span className="text-blue-600 dark:text-blue-400 font-medium">Testimonials</span>
          <h2 className="text-3xl md:text-4xl font-bold mt-2 mb-4 text-gray-900 dark:text-white">
            What Our Clients Say
          </h2>
          <p className="text-gray-600 dark:text-gray-300 text-lg">
            Don't just take our word for it. Here's what our clients have to say about our AI solutions.
          </p>
        </div>

        <div className="relative max-w-4xl mx-auto">
          {/* Mobile View - Single Testimonial */}
          <div className="block md:hidden">
            <Testimonial 
              content={testimonials[currentSlide].content}
              name={testimonials[currentSlide].name}
              role={testimonials[currentSlide].role}
              company={testimonials[currentSlide].company}
              image={testimonials[currentSlide].image}
            />
            <div className="flex justify-center mt-8 gap-4">
              <button 
                onClick={prevSlide}
                className="p-2 rounded-full bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
                aria-label="Previous testimonial"
              >
                <ChevronLeft size={20} />
              </button>
              <button 
                onClick={nextSlide}
                className="p-2 rounded-full bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
                aria-label="Next testimonial"
              >
                <ChevronRight size={20} />
              </button>
            </div>
          </div>

          {/* Desktop View - All Testimonials */}
          <div className="hidden md:grid md:grid-cols-3 gap-8">
            {testimonials.map((testimonial, index) => (
              <Testimonial 
                key={index}
                content={testimonial.content}
                name={testimonial.name}
                role={testimonial.role}
                company={testimonial.company}
                image={testimonial.image}
              />
            ))}
          </div>
        </div>
      </div>
    </section>
  );
};

export default Testimonials;