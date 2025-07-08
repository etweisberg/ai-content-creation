# Sloppy Client

Next.js frontend application for AI TikTok Generation and Content Management.

## Features

### Studio (Content Generation)
Main page for creating and managing video scripts. Users can:
- Submit prompts to generate AI video scripts
- Track scripts through the production pipeline
- Monitor real-time task progress via WebSocket connections
- View and edit generated content

### Cost Management
Dashboard for tracking usage costs and resource consumption across video generation tasks.

### Video Performance (Creator Analytics)
Analytics page showing video performance metrics and engagement data.

## Technical Stack

Built with Next.js 15 and includes:
- React 19 with TypeScript
- Tailwind CSS for styling
- Radix UI components
- Socket.IO client for real-time updates
- Lucide React icons

## Development

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to view the application.
