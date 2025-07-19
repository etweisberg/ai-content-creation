# Sloppy

AI TikTok Generation and Content Management platform for creating and managing video content.

## Deployment

### Docker Setup

The application runs in a containerized environment using Docker Compose with the following services:

- **API Server** (Port 8000): FastAPI backend with Celery task processing
- **Next.js Frontend** (Port 3000): React-based web interface
- **MongoDB** (Port 27017): Database for script and content storage
- **Redis** (Port 6379): Message broker for Celery tasks
- **Celery Worker**: Background task processing for video generation
- **Flower** (Port 5555): Celery task monitoring dashboard

### Quick Start

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Environment Variables

Create a `.env` file in the root directory with necessary configuration for API keys and services.

### Service URLs

- Frontend: http://localhost:3000
- API: http://localhost:8000
- Flower (Task Monitor): http://localhost:5555 (admin:password)
- MongoDB: mongodb://admin:password@localhost:27017

### Demo (i can't edit videos :/)
[🎥 Watch Demo Video](https://drive.google.com/file/d/1tTO1asQQWP5i49H15QkbM4EDRmOA07T1/view)
