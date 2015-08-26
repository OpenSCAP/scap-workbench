/*
 * Copyright 2013 Red Hat Inc., Durham, North Carolina.
 * All Rights Reserved.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * Authors:
 *      Martin Preisler <mpreisle@redhat.com>
 */

#include "DiagnosticsDialog.h"

#include <QAbstractEventDispatcher>
#include <QApplication>
#include <QClipboard>

#include <iostream>
#include <unistd.h>

DiagnosticsDialog::DiagnosticsDialog(QWidget* parent):
    QDialog(parent)
{
    mUI.setupUi(this);

    QObject::connect(
        mUI.clipboardButton, SIGNAL(clicked()),
        this, SLOT(copyToClipboard())
    );

    QObject::connect(
        mUI.closeButton, SIGNAL(clicked()),
        this, SLOT(hide())
    );

    dumpVersionInfo();
}

DiagnosticsDialog::~DiagnosticsDialog()
{}

void DiagnosticsDialog::clear()
{
    mUI.messages->clear();
}

void DiagnosticsDialog::waitUntilHidden(unsigned int interval)
{
    while (isVisible())
    {
        QAbstractEventDispatcher::instance(0)->processEvents(QEventLoop::AllEvents);
        usleep(interval * 1000);
    }
}

void DiagnosticsDialog::infoMessage(const QString& message, MessageFormat format)
{
    pushMessage(MS_INFO, message, format);
}

void DiagnosticsDialog::warningMessage(const QString& message, MessageFormat format)
{
    pushMessage(MS_WARNING, message, format);

    // warning message is important, make sure the diagnostics are shown
    show();
}

void DiagnosticsDialog::errorMessage(const QString& message, MessageFormat format)
{
    pushMessage(MS_ERROR, message, format);

    // error message is important, make sure the diagnostics are shown
    show();
}

void DiagnosticsDialog::exceptionMessage(const std::exception& e, const QString& context, MessageFormat format)
{
    pushMessage(MS_EXCEPTION, (context.isEmpty() ? "" : context + "\n\n" + QString::fromUtf8(e.what())), format);

    // error message is important, make sure the diagnostics are shown
    show();
}


void DiagnosticsDialog::pushMessage(MessageSeverity severity, const QString& fullMessage, MessageFormat format)
{
    char stime[11];
    stime[10] = '\0';

    time_t rawtime;
    struct tm* timeinfo;

    time(&rawtime);
    timeinfo = localtime(&rawtime);

    strftime(stime, 10, "%H:%M:%S", timeinfo);

    QString strSeverity = QObject::tr("unknown");
    QString bgCol = "transparent";
    switch (severity)
    {
        case MS_INFO:
            strSeverity = QObject::tr("info");
            break;
        case MS_WARNING:
            strSeverity = QObject::tr("warning");
            bgCol = "#ffff99";
            break;
        case MS_EXCEPTION:
            strSeverity = QObject::tr("except");
            bgCol = "#cc9933";
            break;
        case MS_ERROR:
            strSeverity = QObject::tr("error");
            bgCol = "#cc9933";
            break;

        default:
            break;
    }

    strSeverity = strSeverity.leftJustified(8);

    std::cerr << stime << " | " << strSeverity.toUtf8().constData() << " | " << fullMessage.toUtf8().constData() << std::endl;
   
    QString outputMessage = fullMessage;
    if (format & MF_XML)
    {
        outputMessage = Qt::escape(outputMessage);
    }
    
    if (format & MF_PREFORMATTED)
    {
        outputMessage = QString("<pre>%1</pre>").arg(outputMessage);
    }
    
    mUI.messages->append(
        QString("<table><tr><td style=\"padding:5px 0px 0px 5px\"><pre>%1 </pre></td><td style=\"background: %2; padding:5px\"><pre>%3 </pre></td><td>%4</td></tr></table>\n")
            .arg(stime, bgCol, strSeverity, outputMessage)
    );
}

void DiagnosticsDialog::dumpVersionInfo()
{
    // We display this in Help->About as well but let us dump it as info message
    // in case workbench crashes before user can work with the GUI.
    infoMessage(QString("SCAP Workbench %1, compiled with Qt %2, using OpenSCAP %3").arg(SCAP_WORKBENCH_VERSION, QT_VERSION_STR, oscap_get_version()));
}

void DiagnosticsDialog::copyToClipboard()
{
    const QString fullLog = mUI.messages->toPlainText();
    QClipboard* clipboard = QApplication::clipboard();
    clipboard->setText(fullLog);
}
