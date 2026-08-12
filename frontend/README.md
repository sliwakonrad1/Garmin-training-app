# AI Sports Coach

Create a dark-themed sports training dashboard called "Garmin AI Trainer".

Navigation sidebar with 3 pages: Dashboard, Activities, AI Coach.

Dashboard page:
- 5 KPI cards: Sessions, Total km, Hours, Calories, VO2max
  fetched from GET http://localhost:8000/api/summary
- Weekly training load bar chart from GET http://localhost:8000/api/weekly
- VO2max trend line chart from GET http://localhost:8000/api/vo2max_trend

Activities page:
- Filter by activity type (pills/buttons)
- Table with: Date, Type, Name, km, min, HR, Calories, Load
  fetched from GET http://localhost:8000/api/activities

AI Coach page:
- Modern chat interface with message bubbles
- Sends POST to http://localhost:8000/api/chat with body {"message": "text"}
- Shows AI response below user message
- Input field at bottom with Send button

Design: dark background #0f0f0f, green accent #22c55e, 
shadcn/ui components, Tailwind CSS, recharts for charts.

This project was built with [Lovable](https://lovable.dev).

## Build with Lovable

Continue developing this project in the [Lovable editor](https://lovable.dev/projects/70d3debe-0d05-4d1a-8883-caa60b27a88d).

- **Ship faster**: describe what you want to build and Lovable handles the code.
- **Stay in sync**: every change made in Lovable is committed straight to this repository.
- **Full ownership**: this code is yours. Push to `main` on GitHub and your changes sync back into Lovable, ready for your next prompt.

## Development

Prefer working locally? You need Node.js and npm — [install with nvm](https://github.com/nvm-sh/nvm#installing-and-updating).

```sh
git clone <this-repository-url>
cd <repository-name>
npm i
npm run dev
```
