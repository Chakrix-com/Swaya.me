# SWAYA UI REDESIGN SPECIFICATION

## Project

Modernise the existing Swaya web application (`test.swaya.me`) while preserving the existing React + Ant Design architecture.

Do not introduce new UI frameworks.

Allowed UI technologies:

- Ant Design
- Tailwind CSS
- Existing React ecosystem libraries already present in the project

Do not replace Ant Design components unless absolutely necessary.
Do not add any other UI library/component/framework without explicit confirmation.

---

# Design Goals

The current application feels like a content management system.

The redesigned application should feel like:

- A modern SaaS platform
- A teacher productivity tool
- A live audience engagement platform

Primary goals:

1. Improve onboarding for new users.
2. Improve discoverability of quiz/poll/exam creation.
3. Reduce visual clutter.
4. Improve mobile and tablet experience.
5. Preserve scalability for users with hundreds of activities.
6. Support nested folders.

---

# Information Hierarchy

The dashboard should follow this order:

1. Welcome / Hero
2. Create Activity
3. Workflow Overview
4. Folder Navigation
5. Activity List
6. Live Sessions
7. Help & Resources

Users should understand what they can create within 5 seconds of opening the application.

---

# Desktop Layout (1280px+)

## Header

Top navigation:

Left:

- Logo
- Workspace selector (future)

Centre:

- Global search

Right:

- Notifications
- Language selector
- User menu

Header height:

- 64px

---

## Hero Section

Full width card.

Contents:

### Left

Heading:

Welcome back, {{UserName}}

Subheading:

Create quizzes, polls and assessments in minutes.

Buttons:

- Create New
- Watch Demo

### Right

Illustration area

Use existing branding assets where possible.

Hero height:

240-280px

---

# Create Activity Section

Immediately below hero.

Heading:

"What would you like to create today?"

Display 4 cards.

## Live Quiz

Description:

Run a quiz in real time.

## Test / Exam

Description:

Timed assessments with auto-grading.

## Live Poll

Description:

Collect instant audience feedback.

## Offline Poll

Description:

Collect responses asynchronously.

Card requirements:

- Large icon
- Description
- Primary action
- Hover state
- Keyboard accessible

Desktop layout:

4 columns

Tablet:

2 columns

Mobile:

2 columns

---

# Workflow Section

Below Create Activity.

Display 3 summary cards.

## Ready to Launch

Activities ready to run.

## In the Works

Draft activities.

## Past Sessions

Completed activities.

Each card should display:

- Count
- Icon
- Short description
- View all action

Desktop:

3 columns

Tablet:

3 columns

Mobile:

Stack vertically

---

# Folder Navigation

Folders must support unlimited nesting.

Use Ant Design Tree component.

Example:

All Activities
├── School
│   ├── Class 8
│   │   ├── Science
│   │   ├── Maths
│   │   └── English
│   ├── Class 9
│   └── Class 10
├── Teacher Training
├── Polls
└── Shared With Me

Requirements:

- Expand/collapse
- Lazy loading
- Drag and drop
- Context menu
- Rename
- Move
- Create folder

Selected folder updates activity list.

---

# Main Content Area

Desktop:

Split layout.

Left:

Folder Tree

Right:

Activities

Layout:

30% / 70%

---

# Activity List

Primary working area.

Display:

Breadcrumbs

Example:

All Activities > School > Class 8 > Science

Then show activity table.

Use Ant Design Table.

Columns:

- Name
- Type
- Status
- Questions
- Last Updated
- Actions

Status Tags:

- Ready to Launch
- Draft
- Live
- Completed

Actions:

- Launch
- Edit
- Continue
- Results
- More

Requirements:

- Sorting
- Filtering
- Search
- Pagination
- Bulk actions

---

# Live Sessions Panel

Desktop only.

Position:

Right side panel.

Width:

320px

Display:

Active sessions.

Each session shows:

- Activity name
- Participant count
- Open Room button
- End Session button

Panel should be collapsible.

---

# Empty States

When user has no activities:

Display:

Create your first activity.

Show:

- Live Quiz
- Test / Exam
- Live Poll
- Offline Poll

Do not display empty tables.

---

# Tablet Layout

Breakpoint:

768px - 1023px

---

## Header

Same as desktop.

Sidebar becomes collapsible drawer.

---

## Hero

Full width.

Reduce illustration size.

---

## Create Activity

2 x 2 grid.

---

## Workflow

3 cards in a horizontal row.

Allow horizontal scrolling if required.

---

## Folder Navigation

Move folder tree into drawer.

Access:

Folders button.

Drawer width:

320px

---

## Activities

Full width.

Activity table remains primary content.

---

## Live Sessions

Collapse into bottom sheet or drawer.

Do not permanently occupy screen width.

---

# Mobile Layout

Breakpoint:

Below 768px

---

# Header

Show:

- Hamburger menu
- Logo
- Notifications

---

# Hero

Compact version.

Stack vertically.

Hide large illustration.

Keep:

- Welcome message
- Create New button

---

# Create Activity

2 x 2 grid.

Large touch targets.

Minimum touch area:

44px

---

# Workflow

Stack vertically.

Order:

Ready
Draft
Past

---

# Folder Navigation

Access via:

Library tab

Display as:

Tree View

Nested folders supported.

---

# Activities

Card layout preferred.

Alternative:

Compact table.

Each activity card shows:

- Title
- Type
- Status
- Actions

---

# Mobile Navigation

Bottom navigation.

Items:

Home
Library
Sessions
More

Floating Create button in centre.

---

# Styling Guidelines

Use Ant Design tokens.

Use Tailwind utilities only for layout and spacing.

Avoid custom CSS where possible.

---

# Visual Improvements

Increase:

- Whitespace
- Border radius
- Typography scale

Reduce:

- Dense tables
- Excessive borders
- Information overload

Target style:

- Linear
- Notion
- Slack
- Modern SaaS dashboards

Avoid:

- ERP appearance
- Legacy admin panel appearance

---

# Accessibility

Must support:

- Keyboard navigation
- Screen readers
- Focus indicators
- WCAG AA contrast

---

# Performance

Requirements:

- Tree lazy loading
- Virtualised activity tables
- Responsive images
- Code splitting

Target:

Lighthouse score > 90

---

# Deliverables

1. Desktop dashboard implementation.
2. Tablet portrait implementation.
3. Tablet landscape implementation.
4. Mobile implementation.
5. Shared responsive component system.
6. Folder tree navigation.
7. Activity management table.
8. Live session panel.
9. Empty state experiences.
10. Updated design tokens using Ant Design theme configuration.


# Colour System

## Design Principles

### Use:

* Soft colours
* Low saturation
* High readability
* Subtle backgrounds

### Avoid:

* Pure bright colours for large surfaces
* Excessive use of red/green
* High contrast panels except for alerts

⸻

Primary Brand Colour

Current Swaya blue can be modernised.

Primary 500: #6366F1
Primary 600: #4F46E5
Primary 100: #E0E7FF
Primary 50 : #EEF2FF

Used for:

* Primary buttons
* Links
* Active navigation
* Focus states

This gives a modern Linear/Notion style appearance.

⸻

Hero Section

Gradient background.

#EEF2FF
to
#F5F3FF

Alternative:

linear-gradient(
135deg,
#EEF2FF,
#FDF4FF
)

This creates the soft purple-blue effect seen in the mockups.

⸻

Create Activity Cards

Each activity type should have its own accent colour.

Live Quiz

Background: #EEF2FF
Icon: #4F46E5

Test / Exam

Background: #ECFDF5
Icon: #059669

Live Poll

Background: #FFF7ED
Icon: #EA580C

Offline Poll

Background: #FDF2F8
Icon: #DB2777

This allows users to distinguish activity types instantly.

⸻

Workflow Cards

Ready to Launch

Background: #ECFDF5
Accent: #10B981

In the Works

Background: #FFF7ED
Accent: #F59E0B

Past Sessions

Background: #EFF6FF
Accent: #3B82F6

⸻

Folder Tree

Folder icons:

#F59E0B

Selected folder:

Background: #EEF2FF
Border: #6366F1

Hover:

Background: #F8FAFC

⸻

Activity Table

Background:

#FFFFFF

Row hover:

#F8FAFC

Borders:

#E5E7EB

Avoid heavy grid lines.

⸻

Status Tags

Ready

Background: #DCFCE7
Text: #166534

Draft

Background: #FEF3C7
Text: #92400E

Live

Background: #DBEAFE
Text: #1D4ED8

Completed

Background: #F3F4F6
Text: #374151

⸻

Sidebar

Instead of:

#001529

(the default Ant Design dark sidebar)

Use:

Background: #FFFFFF
Border: #E5E7EB

or

Background: #F8FAFC

This alone will make Swaya feel significantly more modern.

⸻

Typography

Use:

Heading:
#111827
Body:
#374151
Secondary:
#6B7280

Avoid pure black.

⸻

Ant Design Theme Tokens

Recommended configuration:

token: {
  colorPrimary: '#6366F1',
  colorSuccess: '#10B981',
  colorWarning: '#F59E0B',
  colorError: '#EF4444',
  borderRadius: 12,
  colorBgLayout: '#F8FAFC',
  colorBgContainer: '#FFFFFF',
  colorBorder: '#E5E7EB'
}

