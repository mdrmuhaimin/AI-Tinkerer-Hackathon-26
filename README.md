# AI Conference CRM Agent

## Context

Conferences and networking events create a simple but persistent problem: meeting people is easy, but capturing the useful context from those conversations is not.

A person may collect a business card, remember part of the discussion, and intend to follow up later. By the time they sit down to update a CRM, details are missing, notes are scattered, and duplicate contacts are easy to create.

This project explores a small AI-assisted workflow that captures that information at the moment it is still fresh.

## What We Are Solving

The goal is to reduce the manual work between meeting someone and having a useful CRM record.

The user provides three things:

* the person's name;
* a photo of their business card;
* optionally, a short voice note about the conversation.

The system then turns those inputs into a structured contact record, checks whether the person already exists, and either creates a new record or updates the existing one.

The important part is not simply extracting text from a business card. The system also needs to preserve the context that makes the contact useful later: where the person was met, what was discussed, what opportunities came up, and what might need a follow-up.

## The Intended Experience

The workflow should feel simple from the user's point of view.

The user gives the system the information they already have. The system handles the repetitive work of reading, organizing, checking, and storing it.

If the contact already exists, the system should add useful new information without silently replacing conflicting data. If the contact is new, it should create a clean record without inventing anything that was not present in the source material.

The result should be a CRM that is easier to keep current because capturing a contact requires very little effort.

## Why AI Is Useful Here

Some parts of this workflow are naturally unstructured.

A business card is an image. A voice note is conversational. A useful note such as “met at LEAP, interested in data warehouse consulting, follow up next week” does not arrive as a clean database row.

AI is useful for interpreting those inputs and turning them into structured evidence.

The rest of the workflow should remain controlled by normal software: validating fields, finding existing contacts, deciding when to create or update, writing to the database, and verifying that the intended result was stored.

## First-Version Boundary

The first version is deliberately narrow.

It is not intended to become a complete CRM platform. It does not need sales pipelines, automated outreach, calendar integration, multi-agent collaboration, or autonomous research.

It needs to do one workflow well:

**capture a contact from a business card and optional voice note, store it correctly, and avoid obvious duplicates.**

Later, the stored information can support semantic search and RAG-style questions such as:

> Who did I meet about data warehouse consulting?

> Which people were interested in AI partnerships?

> What did I discuss with this person?

That future capability is useful, but it depends on getting the basic capture workflow right first.

## Success

The project is successful when a user can provide a name, business card image, and optional voice note, and the system reliably turns them into the correct CRM record.

It should preserve useful context, avoid unsupported information, avoid obvious duplicate contacts, and confirm that the intended information was actually stored.

The finished result should remain small enough to understand end to end. That is important because this project is also a learning exercise in building a real AI workflow rather than a collection of disconnected AI features.
